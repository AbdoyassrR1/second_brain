#!/usr/bin/python3
"""Time tracking service for business logic."""

from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo

from flask import current_app

from app.shared.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.shared.logging.audit_log import (
    log_timer_started,
    log_timer_stopped,
    log_timer_auto_stopped,
    log_timer_task_added,
    log_timer_task_removed,
    log_time_entry_created,
    log_time_entry_updated,
    log_time_entry_deleted,
    log_report_generated,
)
from app.shared.metrics import (
    timers_started_total,
    timers_stopped_total,
    timers_auto_stopped_total,
    time_entries_created_total,
    time_entries_deleted_total,
    time_reports_total,
)
from app.features.tasks.repository import TaskRepository
from .repository import TimeEntryRepository
from .exceptions import (
    TaskNotValidError,
    TimerAlreadyRunningError,
    TimerNotRunningError,
    LastTaskRemovalDeniedError,
    TaskNotInTimerError,
    EntryIsRunningError,
    EntryAlreadyStoppedError,
    InvalidTimeRangeError,
)


def even_split(duration_seconds, num_links):
    """Split a duration across ``num_links`` links.

    The remainder seconds go to the FIRST links in position order, so
    ``sum(allocations) == duration_seconds`` exactly.
    """
    base, rem = divmod(duration_seconds, num_links)
    return [base + 1 if i < rem else base for i in range(num_links)]


def _week_start(dt):
    """Monday of the ISO week containing ``dt`` (date object)."""
    return dt.date() - timedelta(days=dt.date().weekday())


def _as_utc(dt):
    """Treat naive datetimes (DB-stored UTC) as aware, convert others to UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class TimeTrackingService:
    """Service for the time tracking feature."""

    def __init__(self):
        self.repository = TimeEntryRepository()
        self.task_repository = TaskRepository()

    # ── Shared building blocks ─────────────────────────────────────────

    def _validate_task_ids(self, task_ids, user_id):
        """Validate 1..N task ids and return ``{task_id: Task}`` for valid ones.

        Any nonexistent / foreign / soft-deleted / archived id raises
        ``TaskNotValidError`` (404) listing every offender, before any write.
        """
        task_ids = [str(tid) for tid in task_ids]
        task_ids = list(dict.fromkeys(task_ids))
        if not task_ids:
            raise ValidationError("task_ids must contain at least one task")

        tasks = {t.id: t for t in self.task_repository.find_by_ids(task_ids)}
        offenders = []
        valid = {}
        for tid in task_ids:
            task = tasks.get(tid)
            if task is None:
                offenders.append({"id": tid, "reason": "not_found"})
            elif task.user_id != user_id:
                offenders.append({"id": tid, "reason": "foreign"})
            elif task.is_deleted:
                offenders.append({"id": tid, "reason": "soft_deleted"})
            elif task.is_archived:
                offenders.append({"id": tid, "reason": "archived"})
            else:
                valid[tid] = task
        if offenders:
            raise TaskNotValidError(offenders)
        return valid

    def _finalize(self, entry):
        """Shared stop core: compute floor duration + split, conditional-update commit.

        Returns the completed entry, or ``None`` if it was already stopped.
        """
        now = datetime.now(UTC)
        started = _as_utc(entry.started_at)
        duration = int((now - started).total_seconds())
        links = sorted(
            entry.task_links,
            key=lambda link: (link.position, link.created_at, link.time_entry_id),
        )
        allocations = even_split(duration, len(links))
        return self.repository.finalize_stop(entry.id, now, duration, allocations)

    # ── Timer ──────────────────────────────────────────────────────────

    def start_timer(self, user_id, task_ids, note=None):
        """Start a running timer linked to 1..N tasks (server-stamped start)."""
        self.repository.lock_user_for_timer(user_id)
        if self.repository.find_running(user_id):
            raise TimerAlreadyRunningError()
        valid_tasks = self._validate_task_ids(task_ids, user_id)

        task_links = [
            (task_id, task.title) for task_id, task in valid_tasks.items()
        ]
        entry = self.repository.create_running(
            user_id, datetime.now(UTC), note, task_links
        )
        log_timer_started(user_id, entry.id, list(valid_tasks.keys()))
        timers_started_total.inc()
        return entry

    def get_current_timer(self, user_id):
        """Return the user's running timer entry (or None). Read-only."""
        return self.repository.find_running(user_id)

    def add_tasks_to_timer(self, user_id, task_ids):
        """Add tasks to the running timer; already-linked ids are skipped."""
        self.repository.lock_user_for_timer(user_id)
        entry = self.repository.find_running(user_id)
        if not entry:
            raise TimerNotRunningError()
        valid_tasks = self._validate_task_ids(task_ids, user_id)

        existing = {link.task_id for link in entry.task_links}
        to_add = [
            (task_id, task.title)
            for task_id, task in valid_tasks.items()
            if task_id not in existing
        ]
        skipped = [tid for tid in valid_tasks if tid in existing]

        added = []
        if to_add:
            added_links = self.repository.add_task_links(entry.id, to_add)
            added = [link.task_id for link in added_links]

        log_timer_task_added(user_id, entry.id, added, skipped)
        return self.repository.get_entry_with_links(entry.id), added, skipped

    def remove_task_from_timer(self, user_id, task_id):
        """Remove a task link from the running timer."""
        self.repository.lock_user_for_timer(user_id)
        entry = self.repository.find_running(user_id)
        if not entry:
            raise TimerNotRunningError()
        task_id = str(task_id)
        if task_id not in {link.task_id for link in entry.task_links}:
            raise TaskNotInTimerError()
        if len(entry.task_links) <= 1:
            raise LastTaskRemovalDeniedError()
        self.repository.remove_task_link(entry.id, task_id)
        log_timer_task_removed(user_id, entry.id, task_id)
        return self.repository.get_entry_with_links(entry.id)

    def stop_timer(self, user_id):
        """Stop the running timer, splitting the duration across linked tasks."""
        self.repository.lock_user_for_timer(user_id)
        entry = self.repository.find_running(user_id)
        if not entry:
            raise TimerNotRunningError()
        completed = self._finalize(entry)
        if completed is None:
            raise EntryAlreadyStoppedError()
        allocations = [
            link.allocated_seconds for link in completed.task_links
        ]
        log_timer_stopped(
            user_id, completed.id, completed.duration_seconds, allocations
        )
        timers_stopped_total.inc()
        time_entries_created_total.labels(source="timer").inc()
        return completed

    def stop_long_running_entry(self, entry_id, reason="24h_limit"):
        """Celery path: complete a stale running entry (idempotent)."""
        entry = self.repository.get_entry_with_links(entry_id)
        if not entry or not entry.running:
            return False
        completed = self._finalize(entry)
        if completed is None:
            return False
        log_timer_auto_stopped(
            completed.user_id, completed.id, completed.duration_seconds, reason
        )
        timers_auto_stopped_total.inc()
        time_entries_created_total.labels(source="timer").inc()
        return True

    def auto_stop_for_user(self, user_id, reason="account_deleted"):
        """Account-delete path: stop any running timer before user soft-delete."""
        self.repository.lock_user_for_timer(user_id)
        entry = self.repository.find_running(user_id)
        if not entry:
            return {"stopped": False}
        entry = self.repository.get_entry_with_links(entry.id)
        completed = self._finalize(entry)
        if completed is None:
            return {"stopped": False}
        log_timer_auto_stopped(
            user_id, completed.id, completed.duration_seconds, reason
        )
        timers_auto_stopped_total.inc()
        time_entries_created_total.labels(source="timer").inc()
        return {"stopped": True}

    def tasks_in_running_timer(self, task_ids, user_id=None):
        """Cross-feature guard: tasks linked to a running timer."""
        task_ids = [str(tid) for tid in task_ids]
        if not task_ids:
            return []
        return [
            {"task_id": task_id, "time_entry_id": time_entry_id}
            for task_id, time_entry_id in self.repository.find_task_ids_in_running_timers(
                task_ids, user_id=user_id
            )
        ]

    # ── Manual entries ─────────────────────────────────────────────────

    def create_entry(self, user_id, task_ids, started_at, ended_at, note=None):
        """Create a completed (manual) time entry with immediate split."""
        valid_tasks = self._validate_task_ids(task_ids, user_id)
        duration = int((ended_at - started_at).total_seconds())
        task_links = [
            (task_id, task.title, allocated)
            for task_id, task, allocated in zip(
                valid_tasks.keys(),
                valid_tasks.values(),
                even_split(duration, len(valid_tasks)),
            )
        ]
        entry = self.repository.create_entry_with_links(
            user_id, started_at, ended_at, duration, note, task_links
        )
        log_time_entry_created(
            user_id, entry.id, list(valid_tasks.keys()), duration, "manual"
        )
        time_entries_created_total.labels(source="manual").inc()
        return entry

    def get_entry(self, entry_id, user_id):
        """Fetch an entry with ownership guard."""
        entry = self.repository.find_by_id(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found")
        if entry.user_id != user_id:
            raise ForbiddenError("Not authorized to access this time entry")
        return entry

    def list_entries(
        self,
        user_id,
        from_dt=None,
        to_dt=None,
        task_id=None,
        running=None,
        page=1,
        per_page=20,
    ):
        """List entries with filters and pagination."""
        if from_dt is not None and to_dt is not None and from_dt > to_dt:
            raise InvalidTimeRangeError("from must be less than or equal to to")
        return self.repository.find_by_user(
            user_id,
            from_dt=from_dt,
            to_dt=to_dt,
            task_id=task_id,
            running=running,
            page=page,
            per_page=per_page,
        )

    def update_entry(self, entry_id, user_id, changes):
        """Patch an entry: note / started_at / ended_at / task_ids (re-split).

        Running entries accept note-only; time/task fields raise 409.
        """
        entry = self.repository.get_entry_with_links(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found")
        if entry.user_id != user_id:
            raise ForbiddenError("Not authorized to access this time entry")

        if entry.running:
            if any(key in changes for key in ("started_at", "ended_at", "task_ids")):
                raise EntryIsRunningError()
            if "note" in changes:
                self.repository.update_fields(entry_id, note=changes["note"])
            log_time_entry_updated(user_id, entry_id, list(changes.keys()))
            return self.repository.get_entry_with_links(entry_id)

        new_started = _as_utc(changes.get("started_at", entry.started_at))
        new_ended = _as_utc(changes.get("ended_at", entry.ended_at))
        if new_started >= new_ended:
            raise ValidationError("ended_at must be after started_at")
        duration = int((new_ended - new_started).total_seconds())

        time_fields_changed = "started_at" in changes or "ended_at" in changes
        task_links = None

        if "task_ids" in changes:
            valid_tasks = self._validate_task_ids(changes["task_ids"], user_id)
            if not valid_tasks:
                raise ValidationError("task_ids must contain at least one valid task")
            task_links = [
                (task_id, task.title, allocated)
                for task_id, task, allocated in zip(
                    valid_tasks.keys(),
                    valid_tasks.values(),
                    even_split(duration, len(valid_tasks)),
                )
            ]
        elif time_fields_changed:
            ordered = sorted(
                entry.task_links,
                key=lambda link: (link.position, link.created_at, link.time_entry_id),
            )
            task_links = [
                (link.task_id, link.task_title, allocated)
                for link, allocated in zip(
                    ordered, even_split(duration, len(ordered))
                )
            ]

        fields = {}
        if time_fields_changed:
            fields["started_at"] = new_started
            fields["ended_at"] = new_ended
            fields["duration_seconds"] = duration
        if "note" in changes:
            fields["note"] = changes["note"]
        if fields:
            self.repository.update_fields(entry_id, **fields)
        if task_links is not None:
            self.repository.replace_task_links(entry_id, task_links)

        log_time_entry_updated(user_id, entry_id, list(changes.keys()))
        return self.repository.get_entry_with_links(entry_id)

    def delete_entry(self, entry_id, user_id):
        """Hard-delete a completed entry (running entries are 409)."""
        entry = self.repository.find_by_id(entry_id)
        if not entry:
            raise NotFoundError("Time entry not found")
        if entry.user_id != user_id:
            raise ForbiddenError("Not authorized to access this time entry")
        if entry.running:
            raise EntryIsRunningError()
        self.repository.delete_entry(entry_id)
        log_time_entry_deleted(user_id, entry_id)
        time_entries_deleted_total.inc()

    # ── Reports ────────────────────────────────────────────────────────

    def generate_report(self, user_id, group_by, from_dt, to_dt, tz="UTC"):
        """Aggregate completed entries in [from_dt, to_dt], bucketed in ``tz``."""
        if from_dt > to_dt:
            raise InvalidTimeRangeError("from must be less than or equal to to")
        max_days = current_app.config.get("TIME_REPORT_MAX_DAYS", 366)
        if (to_dt - from_dt).days > max_days:
            raise InvalidTimeRangeError(
                f"Report range cannot exceed {max_days} days"
            )
        try:
            zone = ZoneInfo(tz)
        except Exception:
            raise ValidationError("tz must be a valid IANA timezone name")

        entries = self.repository.find_completed_in_range(user_id, from_dt, to_dt)
        totals = self.repository.aggregate_completed(user_id, from_dt, to_dt)

        if group_by in ("day", "week"):
            groups = self._bucket_by_time(entries, from_dt, to_dt, zone, group_by)
        elif group_by == "task":
            groups = self._group_by_task(entries)
        else:
            groups = self._group_by_project(entries)

        log_report_generated(user_id, group_by, from_dt, to_dt, tz)
        time_reports_total.inc()
        return {
            "group_by": group_by,
            "tz": tz,
            "from_": from_dt,
            "to_": to_dt,
            "totals": totals,
            "groups": groups,
        }

    def _bucket_by_time(self, entries, from_dt, to_dt, zone, group_by):
        """Day/week buckets with a complete (zero-filled) axis."""
        from datetime import date

        start = from_dt.astimezone(zone)
        end = to_dt.astimezone(zone)
        buckets = {}

        if group_by == "day":
            current = start.date()
            last = end.date()
            while current <= last:
                buckets[current.isoformat()] = {
                    "date": current.isoformat(),
                    "total_seconds": 0,
                    "entry_count": 0,
                }
                current += timedelta(days=1)
            for entry in entries:
                key = _as_utc(entry.started_at).astimezone(zone).date().isoformat()
                if key in buckets:
                    buckets[key]["total_seconds"] += entry.duration_seconds or 0
                    buckets[key]["entry_count"] += 1
            return list(buckets.values())

        current = _week_start(start)
        last = _week_start(end)
        while current <= last:
            key = current.isoformat()
            buckets[key] = {
                "week_start": key,
                "total_seconds": 0,
                "entry_count": 0,
            }
            current += timedelta(days=7)
        for entry in entries:
            key = _week_start(_as_utc(entry.started_at).astimezone(zone)).isoformat()
            if key in buckets:
                buckets[key]["total_seconds"] += entry.duration_seconds or 0
                buckets[key]["entry_count"] += 1
        return list(buckets.values())

    def _group_by_task(self, entries):
        """Per-task totals from link allocations."""
        groups = {}
        for entry in entries:
            for link in entry.task_links:
                group = groups.setdefault(
                    link.task_id,
                    {
                        "task_id": link.task_id,
                        "task_title": link.task_title,
                        "total_seconds": 0,
                        "entry_count": 0,
                        "is_deleted": bool(link.is_deleted),
                    },
                )
                group["total_seconds"] += link.allocated_seconds or 0
                group["entry_count"] += 1
        return list(groups.values())

    def _group_by_project(self, entries):
        """Per-project rollup via link->task->project; null project -> no_project."""
        groups = {}
        for entry in entries:
            for link in entry.task_links:
                task = getattr(link, "task", None)
                project = getattr(task, "project", None) if task else None
                project_id = project.id if project else None
                key = project_id or "no_project"
                group = groups.setdefault(
                    key,
                    {
                        "project_id": project_id,
                        "project_title": project.name if project else "no_project",
                        "total_seconds": 0,
                    },
                )
                group["total_seconds"] += link.allocated_seconds or 0
        return list(groups.values())
