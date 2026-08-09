#!/usr/bin/python3
"""Tests for time tracking service business logic."""

import pytest
from datetime import datetime, timedelta, UTC

from app.features.time_tracking.service import (
    TimeTrackingService,
    even_split,
)
from app.features.time_tracking.exceptions import (
    TaskNotValidError,
    TimerAlreadyRunningError,
    TimerNotRunningError,
    LastTaskRemovalDeniedError,
    TaskNotInTimerError,
    EntryIsRunningError,
    EntryAlreadyStoppedError,
    InvalidTimeRangeError,
)
from app.features.tasks.service import TaskService
from app.shared.exceptions import NotFoundError, ForbiddenError, ValidationError


def _make_tasks(user_id, count=2):
    task_service = TaskService()
    return [
        task_service.create_task(user_id=user_id, title=f"Task {i}")
        for i in range(count)
    ]


class TestEvenSplit:
    """Test the duration splitter."""

    def test_exact_division(self):
        assert even_split(90, 3) == [30, 30, 30]

    def test_remainder_goes_to_first_links(self):
        assert even_split(91, 3) == [31, 30, 30]
        assert sum(even_split(91, 3)) == 91

    def test_single_link(self):
        assert even_split(60, 1) == [60]

    def test_sum_always_matches_duration(self):
        for duration in range(1, 100):
            for num in range(1, 6):
                assert sum(even_split(duration, num)) == duration


class TestTimerLifecycle:
    """Test the start/current/stop timer flow."""

    def test_start_timer(self, db, verified_user):
        tasks = _make_tasks(verified_user.id)
        service = TimeTrackingService()
        entry = service.start_timer(
            verified_user.id, [t.id for t in tasks], note="focus"
        )
        assert entry.running is True
        assert entry.started_at is not None
        assert entry.ended_at is None
        assert entry.duration_seconds is None
        assert len(entry.task_links) == 2
        assert {link.task_id for link in entry.task_links} == {
            t.id for t in tasks
        }

    def test_start_second_timer_fails(self, db, verified_user):
        tasks = _make_tasks(verified_user.id)
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [tasks[0].id])
        with pytest.raises(TimerAlreadyRunningError):
            service.start_timer(verified_user.id, [tasks[1].id])

    def test_start_with_invalid_task(self, db, verified_user):
        tasks = _make_tasks(verified_user.id)
        service = TimeTrackingService()
        with pytest.raises(TaskNotValidError) as exc:
            service.start_timer(verified_user.id, [tasks[0].id, "missing-id"])
        reasons = {o["id"]: o["reason"] for o in exc.value.errors["task_ids"]}
        assert reasons["missing-id"] == "not_found"

    def test_start_with_foreign_task(self, db, verified_user):
        other = _make_tasks("other-user-id", count=1)
        service = TimeTrackingService()
        with pytest.raises(TaskNotValidError) as exc:
            service.start_timer(verified_user.id, [other[0].id])
        assert exc.value.errors["task_ids"][0]["reason"] == "foreign"

    def test_start_with_deleted_and_archived_tasks(self, db, verified_user):
        task_service = TaskService()
        deleted = task_service.create_task(user_id=verified_user.id, title="Del")
        archived = task_service.create_task(user_id=verified_user.id, title="Arc")
        task_service.delete_task(deleted.id, verified_user.id)
        task_service.archive_task(archived.id, verified_user.id)

        service = TimeTrackingService()
        with pytest.raises(TaskNotValidError) as exc:
            service.start_timer(verified_user.id, [deleted.id, archived.id])
        reasons = {o["id"]: o["reason"] for o in exc.value.errors["task_ids"]}
        assert reasons[deleted.id] == "soft_deleted"
        assert reasons[archived.id] == "archived"

    def test_duplicate_task_ids_deduped(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id, task.id])
        assert len(entry.task_links) == 1

    def test_get_current_timer(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        assert service.get_current_timer(verified_user.id) is None
        service.start_timer(verified_user.id, [task.id])
        current = service.get_current_timer(verified_user.id)
        assert current is not None and current.running is True

    def test_add_tasks_to_timer(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=3)
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [tasks[0].id])
        entry, added, skipped = service.add_tasks_to_timer(
            verified_user.id, [tasks[1].id, tasks[2].id]
        )
        assert set(added) == {tasks[1].id, tasks[2].id}
        assert skipped == []
        assert {link.task_id for link in entry.task_links} == {
            t.id for t in tasks
        }

    def test_add_tasks_to_timer_skips_existing(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [tasks[0].id])
        entry, added, skipped = service.add_tasks_to_timer(
            verified_user.id, [tasks[0].id, tasks[1].id]
        )
        assert added == [tasks[1].id]
        assert skipped == [tasks[0].id]
        assert len(entry.task_links) == 2

    def test_add_tasks_with_no_running_timer(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        with pytest.raises(TimerNotRunningError):
            service.add_tasks_to_timer(verified_user.id, [task.id])

    def test_remove_task_from_timer(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [t.id for t in tasks])
        entry = service.remove_task_from_timer(verified_user.id, tasks[0].id)
        assert {link.task_id for link in entry.task_links} == {tasks[1].id}

    def test_remove_last_task_denied(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [task.id])
        with pytest.raises(LastTaskRemovalDeniedError):
            service.remove_task_from_timer(verified_user.id, task.id)

    def test_remove_task_not_in_timer(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [tasks[0].id])
        with pytest.raises(TaskNotInTimerError):
            service.remove_task_from_timer(verified_user.id, tasks[1].id)

    def test_stop_timer_splits_duration(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=3)
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [t.id for t in tasks])

        # Backdate the start to make the duration deterministic (90s).
        from app.shared.database import database
        entry.started_at = datetime.now(UTC) - timedelta(seconds=90)
        database.commit()

        completed = service.stop_timer(verified_user.id)
        assert completed.running is False
        assert completed.ended_at is not None
        assert completed.duration_seconds == 90
        allocations = [
            link.allocated_seconds for link in completed.task_links
        ]
        assert allocations == [30, 30, 30]

    def test_stop_timer_with_remainder(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [t.id for t in tasks])
        from app.shared.database import database
        entry.started_at = datetime.now(UTC) - timedelta(seconds=91)
        database.commit()

        completed = service.stop_timer(verified_user.id)
        assert completed.duration_seconds == 91
        allocations = [
            link.allocated_seconds for link in completed.task_links
        ]
        assert sorted(allocations, reverse=True) == [46, 45]
        assert sum(allocations) == 91

    def test_stop_timer_with_no_running_timer(self, db, verified_user):
        service = TimeTrackingService()
        with pytest.raises(TimerNotRunningError):
            service.stop_timer(verified_user.id)

    def test_stop_timer_idempotency(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [task.id])
        service.stop_timer(verified_user.id)
        with pytest.raises(TimerNotRunningError):
            service.stop_timer(verified_user.id)


class TestManualEntries:
    """Test manual (completed) entry creation and mutation."""

    def test_create_entry(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        end = start + timedelta(minutes=61)
        entry = service.create_entry(
            verified_user.id, [t.id for t in tasks], start, end, note="manual"
        )
        assert entry.running is False
        assert entry.duration_seconds == 3660
        allocations = [
            link.allocated_seconds for link in entry.task_links
        ]
        assert allocations == [1830, 1830]

    def test_create_entry_with_remainder_keeps_sum(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=3)
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        end = start + timedelta(seconds=92)
        entry = service.create_entry(
            verified_user.id, [t.id for t in tasks], start, end
        )
        allocations = [link.allocated_seconds for link in entry.task_links]
        assert sum(allocations) == 92

    def test_get_entry_ownership(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        entry = service.create_entry(
            verified_user.id, [task.id], start, start + timedelta(minutes=30)
        )
        assert service.get_entry(entry.id, verified_user.id).id == entry.id
        with pytest.raises(NotFoundError):
            service.get_entry("missing", verified_user.id)
        with pytest.raises(ForbiddenError):
            service.get_entry(entry.id, "other-user-id")

    def test_list_entries_with_filters(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=1)
        service = TimeTrackingService()
        day1 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        day2 = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
        service.create_entry(
            verified_user.id, [tasks[0].id], day1, day1 + timedelta(minutes=30)
        )
        service.create_entry(
            verified_user.id, [tasks[0].id], day2, day2 + timedelta(minutes=30)
        )
        page = service.list_entries(
            verified_user.id, from_dt=day1, to_dt=day1 + timedelta(hours=23)
        )
        assert page.total == 1

    def test_list_entries_invalid_range(self, db, verified_user):
        service = TimeTrackingService()
        with pytest.raises(InvalidTimeRangeError):
            service.list_entries(
                verified_user.id,
                from_dt=datetime(2026, 1, 2, tzinfo=UTC),
                to_dt=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_update_entry_note(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        entry = service.create_entry(
            verified_user.id, [task.id], start, start + timedelta(minutes=30)
        )
        updated = service.update_entry(entry.id, verified_user.id, {"note": "hi"})
        assert updated.note == "hi"

    def test_update_entry_time_reallocates(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        entry = service.create_entry(
            verified_user.id, [t.id for t in tasks], start, start + timedelta(minutes=60)
        )
        updated = service.update_entry(
            entry.id, verified_user.id, {"ended_at": start + timedelta(minutes=62)}
        )
        assert updated.duration_seconds == 3720
        allocations = [link.allocated_seconds for link in updated.task_links]
        assert allocations == [1860, 1860]

    def test_update_entry_replace_tasks(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        entry = service.create_entry(
            verified_user.id, [tasks[0].id], start, start + timedelta(minutes=60)
        )
        updated = service.update_entry(
            entry.id, verified_user.id, {"task_ids": [tasks[1].id]}
        )
        assert [link.task_id for link in updated.task_links] == [tasks[1].id]
        assert updated.task_links[0].allocated_seconds == 3600

    def test_update_running_entry_time_denied(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id])
        with pytest.raises(EntryIsRunningError):
            service.update_entry(
                entry.id,
                verified_user.id,
                {"started_at": datetime(2026, 1, 1, tzinfo=UTC)},
            )

    def test_update_running_entry_note_ok(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id])
        updated = service.update_entry(entry.id, verified_user.id, {"note": "n"})
        assert updated.note == "n"

    def test_delete_entry(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        entry = service.create_entry(
            verified_user.id, [task.id], start, start + timedelta(minutes=30)
        )
        service.delete_entry(entry.id, verified_user.id)
        with pytest.raises(NotFoundError):
            service.get_entry(entry.id, verified_user.id)

    def test_delete_running_entry_denied(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id])
        with pytest.raises(EntryIsRunningError):
            service.delete_entry(entry.id, verified_user.id)


class TestReports:
    """Test report aggregation."""

    def _seed(self, user_id, tasks):
        service = TimeTrackingService()
        entries = []
        start = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)  # Monday
        for i, task in enumerate(tasks):
            e_start = start + timedelta(days=i)
            entries.append(
                service.create_entry(
                    user_id,
                    [task.id],
                    e_start,
                    e_start + timedelta(minutes=60),
                )
            )
        return entries

    def test_report_day_buckets_zero_filled(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=1)
        self._seed(verified_user.id, tasks)
        service = TimeTrackingService()
        report = service.generate_report(
            verified_user.id,
            "day",
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 3, tzinfo=UTC),
        )
        assert report["totals"]["total_seconds"] == 3600
        assert len(report["groups"]) == 2
        assert report["groups"][0]["date"] == "2026-03-02"
        assert report["groups"][0]["total_seconds"] == 3600
        assert report["groups"][1]["total_seconds"] == 0

    def test_report_week_buckets(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=1)
        self._seed(verified_user.id, tasks)
        service = TimeTrackingService()
        report = service.generate_report(
            verified_user.id,
            "week",
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 8, tzinfo=UTC),
        )
        assert report["totals"]["entry_count"] == 1
        assert report["groups"][0]["week_start"] == "2026-03-02"

    def test_report_group_by_task(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        self._seed(verified_user.id, tasks)
        service = TimeTrackingService()
        report = service.generate_report(
            verified_user.id,
            "task",
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 4, tzinfo=UTC),
        )
        by_id = {g["task_id"]: g for g in report["groups"]}
        assert by_id[tasks[0].id]["total_seconds"] == 3600
        assert by_id[tasks[0].id]["task_title"] == "Task 0"

    def test_report_group_by_project(self, db, verified_user):
        from app.features.projects.models import Project
        from app.shared.database import database

        task = _make_tasks(verified_user.id, count=1)[0]
        project = Project(user_id=verified_user.id, name="Alpha")
        database.add(project)
        database.commit()
        task.project_id = project.id
        database.commit()

        service = TimeTrackingService()
        start = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
        service.create_entry(
            verified_user.id, [task.id], start, start + timedelta(minutes=60)
        )
        report = service.generate_report(
            verified_user.id,
            "project",
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 3, tzinfo=UTC),
        )
        assert report["groups"][0]["project_id"] == project.id
        assert report["groups"][0]["total_seconds"] == 3600

    def test_report_group_by_project_no_project(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        start = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)
        service.create_entry(
            verified_user.id, [task.id], start, start + timedelta(minutes=60)
        )
        report = service.generate_report(
            verified_user.id,
            "project",
            datetime(2026, 3, 2, tzinfo=UTC),
            datetime(2026, 3, 3, tzinfo=UTC),
        )
        assert report["groups"][0]["project_id"] is None
        assert report["groups"][0]["project_title"] == "no_project"

    def test_report_invalid_range(self, db, verified_user):
        service = TimeTrackingService()
        with pytest.raises(InvalidTimeRangeError):
            service.generate_report(
                verified_user.id,
                "day",
                datetime(2026, 3, 3, tzinfo=UTC),
                datetime(2026, 3, 2, tzinfo=UTC),
            )

    def test_report_bad_timezone(self, db, verified_user):
        service = TimeTrackingService()
        with pytest.raises(ValidationError):
            service.generate_report(
                verified_user.id,
                "day",
                datetime(2026, 3, 2, tzinfo=UTC),
                datetime(2026, 3, 3, tzinfo=UTC),
                tz="Not/AZone",
            )


class TestCrossFeatureGuard:
    """Test the guard used by the tasks feature."""

    def test_tasks_in_running_timer(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=2)
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [tasks[0].id])
        offenders = service.tasks_in_running_timer(
            [tasks[0].id, tasks[1].id], verified_user.id
        )
        assert len(offenders) == 1
        assert offenders[0]["task_id"] == tasks[0].id
        assert offenders[0]["time_entry_id"] == entry.id

    def test_no_running_timer_returns_empty(self, db, verified_user):
        tasks = _make_tasks(verified_user.id, count=1)
        service = TimeTrackingService()
        assert (
            service.tasks_in_running_timer([tasks[0].id], verified_user.id) == []
        )


class TestAutoStop:
    """Test the sweep and account-delete stop paths."""

    def test_stop_long_running_entry(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id])
        from app.shared.database import database
        entry.started_at = datetime.now(UTC) - timedelta(hours=25)
        database.commit()

        assert service.stop_long_running_entry(entry.id, reason="24h_limit") is True
        refreshed = service.get_entry(entry.id, verified_user.id)
        assert refreshed.running is False
        assert refreshed.duration_seconds == 25 * 3600

    def test_stop_long_running_idempotent(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        entry = service.start_timer(verified_user.id, [task.id])
        from app.shared.database import database
        entry.started_at = datetime.now(UTC) - timedelta(hours=25)
        database.commit()

        assert service.stop_long_running_entry(entry.id) is True
        assert service.stop_long_running_entry(entry.id) is False

    def test_auto_stop_for_user(self, db, verified_user):
        task = _make_tasks(verified_user.id, count=1)[0]
        service = TimeTrackingService()
        service.start_timer(verified_user.id, [task.id])
        result = service.auto_stop_for_user(verified_user.id, reason="account_deleted")
        assert result == {"stopped": True}

    def test_auto_stop_for_user_no_timer(self, db, verified_user):
        service = TimeTrackingService()
        assert (
            service.auto_stop_for_user(verified_user.id, reason="account_deleted")
            == {"stopped": False}
        )
