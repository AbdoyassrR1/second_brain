#!/usr/bin/python3
"""Time tracking repository for database operations."""

from app.extensions import db
from app.shared.database import database
from .models import TimeEntry, TimeEntryTask


class TimeEntryRepository:
    """Repository for TimeEntry and TimeEntryTask operations."""

    @staticmethod
    def lock_user_for_timer(user_id):
        """Serialize timer mutations per user (SELECT ... FOR UPDATE on the user row).

        MySQL InnoDB honors the row lock; SQLite ignores ``FOR UPDATE`` but
        serializes writes at the DB level, so tests are unaffected.
        """
        from app.features.auth.models import User

        return database.session.execute(
            db.select(User).where(User.id == user_id).with_for_update()
        ).scalar_one_or_none()

    @staticmethod
    def find_running(user_id):
        """Find the user's running timer entry, if any."""
        return TimeEntry.query.filter_by(user_id=user_id, running=True).first()

    @staticmethod
    def find_long_running(cutoff, limit=200):
        """Find running entries started before ``cutoff``, oldest first (for the auto-stop job)."""
        if cutoff.tzinfo is not None:
            cutoff = cutoff.replace(tzinfo=None)
        return (
            TimeEntry.query.filter(
                TimeEntry.running == True,
                TimeEntry.started_at < cutoff,
            )
            .order_by(TimeEntry.started_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_entry_with_links(entry_id, for_update=False):
        """Load an entry with its task links in split order."""
        query = TimeEntry.query.options(
            db.joinedload(TimeEntry.task_links)
        ).filter_by(id=entry_id)
        if for_update:
            query = query.with_for_update()
        return query.first()

    @staticmethod
    def create_running(user_id, started_at, note, task_links):
        """Create a running timer entry plus its task links (one transaction).

        Args:
            task_links: list of (task_id, task_title) in position order.
        """
        entry = TimeEntry(
            user_id=user_id, started_at=started_at, running=True, note=note
        )
        database.add(entry)
        database.session.flush()
        for position, (task_id, title) in enumerate(task_links):
            database.add(
                TimeEntryTask(
                    time_entry_id=entry.id,
                    task_id=task_id,
                    task_title=title,
                    position=position,
                )
            )
        database.commit()
        return entry

    @staticmethod
    def add_task_links(entry_id, task_links):
        """Insert only new task links (existing PKs skipped, idempotent). One commit.

        Args:
            task_links: list of (task_id, task_title).
        Returns:
            list of added TimeEntryTask rows.
        """
        existing = {
            link.task_id
            for link in TimeEntryTask.query.filter_by(time_entry_id=entry_id).all()
        }
        next_position = (
            database.session.query(
                db.func.coalesce(db.func.max(TimeEntryTask.position), -1)
            )
            .filter_by(time_entry_id=entry_id)
            .scalar()
        ) + 1
        added = []
        for task_id, title in task_links:
            if task_id in existing:
                continue
            existing.add(task_id)
            link = TimeEntryTask(
                time_entry_id=entry_id,
                task_id=task_id,
                task_title=title,
                position=next_position,
            )
            next_position += 1
            database.add(link)
            added.append(link)
        database.commit()
        return added

    @staticmethod
    def remove_task_link(entry_id, task_id):
        """Delete one task link. One commit."""
        link = TimeEntryTask.query.filter_by(
            time_entry_id=entry_id, task_id=task_id
        ).first()
        if not link:
            return False
        database.delete(link)
        database.commit()
        return True

    @staticmethod
    def finalize_stop(entry_id, ended_at, duration_seconds, allocations):
        """Complete a running entry with a conditional update (race-safe).

        Sets running=False and the duration via ``UPDATE ... WHERE running=True``.
        If 0 rows matched (already stopped), rolls back and returns ``None``.
        Otherwise assigns per-link allocations and commits once.
        """
        result = database.session.execute(
            db.update(TimeEntry)
            .where(TimeEntry.id == entry_id, TimeEntry.running == True)
            .values(
                running=False,
                ended_at=ended_at,
                duration_seconds=duration_seconds,
            )
        )
        if result.rowcount == 0:
            database.rollback()
            return None
        links = (
            TimeEntryTask.query.filter_by(time_entry_id=entry_id)
            .order_by(TimeEntryTask.position.asc())
            .all()
        )
        for link, seconds in zip(links, allocations):
            link.allocated_seconds = seconds
        database.commit()
        return TimeEntry.query.get(entry_id)

    @staticmethod
    def create_entry_with_links(
        user_id, started_at, ended_at, duration_seconds, note, task_links
    ):
        """Create a completed (manual) entry plus links with allocations. One transaction.

        Args:
            task_links: list of (task_id, task_title, allocated_seconds) in position order.
        """
        entry = TimeEntry(
            user_id=user_id,
            started_at=started_at,
            ended_at=ended_at,
            duration_seconds=duration_seconds,
            running=False,
            note=note,
        )
        database.add(entry)
        database.session.flush()
        for position, (task_id, title, allocated) in enumerate(task_links):
            database.add(
                TimeEntryTask(
                    time_entry_id=entry.id,
                    task_id=task_id,
                    task_title=title,
                    position=position,
                    allocated_seconds=allocated,
                )
            )
        database.commit()
        return entry

    @staticmethod
    def find_by_id(entry_id):
        """Find an entry by id (unscoped; ownership checked in the service)."""
        return TimeEntry.query.get(entry_id)

    @staticmethod
    def find_by_user(
        user_id,
        from_dt=None,
        to_dt=None,
        task_id=None,
        running=None,
        page=1,
        per_page=20,
    ):
        """List entries scoped to a user with filters and pagination."""
        query = TimeEntry.query.filter_by(user_id=user_id)
        if from_dt is not None:
            query = query.filter(TimeEntry.started_at >= from_dt)
        if to_dt is not None:
            query = query.filter(TimeEntry.started_at <= to_dt)
        if task_id is not None:
            query = query.filter(
                TimeEntry.task_links.any(TimeEntryTask.task_id == task_id)
            )
        if running is not None:
            query = query.filter(TimeEntry.running == running)
        query = query.order_by(TimeEntry.started_at.desc())
        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def find_completed_in_range(user_id, from_dt, to_dt):
        """Completed entries whose started_at falls in [from_dt, to_dt], links eager-loaded."""
        return (
            TimeEntry.query.options(
                db.joinedload(TimeEntry.task_links).joinedload(TimeEntryTask.task)
            )
            .filter(
                TimeEntry.user_id == user_id,
                TimeEntry.running == False,
                TimeEntry.started_at >= from_dt,
                TimeEntry.started_at <= to_dt,
            )
            .all()
        )

    @staticmethod
    def aggregate_completed(user_id, from_dt, to_dt):
        """Totals over completed entries in range (portable sum/count)."""
        row = database.session.query(
            db.func.coalesce(db.func.sum(TimeEntry.duration_seconds), 0).label(
                "total_seconds"
            ),
            db.func.count().label("entry_count"),
        ).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.running == False,
            TimeEntry.started_at >= from_dt,
            TimeEntry.started_at <= to_dt,
        ).first()
        return {
            "total_seconds": int(row.total_seconds or 0),
            "entry_count": row.entry_count,
        }

    @staticmethod
    def find_task_ids_in_running_timers(task_ids, user_id=None):
        """Return [(task_id, time_entry_id)] for tasks linked to running timers.

        Used by the tasks-feature guard. One query for all-or-nothing bulk checks.
        """
        query = database.session.query(
            TimeEntryTask.task_id, TimeEntry.id.label("time_entry_id")
        ).join(TimeEntry, TimeEntry.id == TimeEntryTask.time_entry_id).filter(
            TimeEntryTask.task_id.in_(task_ids),
            TimeEntry.running == True,
        )
        if user_id is not None:
            query = query.filter(TimeEntry.user_id == user_id)
        return [(row.task_id, row.time_entry_id) for row in query.all()]

    @staticmethod
    def replace_task_links(entry_id, task_links):
        """Delete existing links and insert new ones with allocations. One commit.

        Args:
            task_links: list of (task_id, task_title, allocated_seconds).
        """
        TimeEntryTask.query.filter_by(time_entry_id=entry_id).delete(
            synchronize_session=False
        )
        database.session.flush()
        for position, (task_id, title, allocated) in enumerate(task_links):
            database.add(
                TimeEntryTask(
                    time_entry_id=entry_id,
                    task_id=task_id,
                    task_title=title,
                    position=position,
                    allocated_seconds=allocated,
                )
            )
        database.commit()

    @staticmethod
    def update_fields(entry_id, **fields):
        """Update simple entry fields (e.g. note). One commit."""
        entry = TimeEntry.query.get(entry_id)
        if entry:
            for key, value in fields.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            database.commit()
        return entry

    @staticmethod
    def delete_entry(entry_id):
        """Hard-delete an entry and its links (delete-orphan cascade). One commit."""
        entry = TimeEntry.query.get(entry_id)
        if not entry:
            return False
        database.delete(entry)
        database.commit()
        return True
