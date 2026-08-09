import pytest
from datetime import datetime
from app.extensions import db as _db
from app.features.reminders.models import Reminder
from app.features.tasks.models import Task
from app.features.auth.models import User
from app.features.auth.repository import RoleRepository
from app.jobs.tasks import dispatch_due_reminders, send_reminder


class TestDispatchDueReminders:
    def test_no_pending_reminders(self, app, db):
        result = dispatch_due_reminders.delay()
        assert result.get(timeout=5) == {"dispatched": 0}

    def test_dispatches_due_reminders(self, app, db):
        role = RoleRepository.find_by_name("customer")
        user = User(
            username="remindertest",
            email="reminder@test.com",
            phone_number="9999999999",
            role_id=role.id,
            is_verified=True,
        )
        user.set_password("Password123")
        _db.session.add(user)
        _db.session.commit()

        task = Task(title="Test Task", user_id=user.id)
        _db.session.add(task)
        _db.session.commit()

        reminder = Reminder(
            task_id=task.id,
            user_id=user.id,
            reminder_time=datetime(2020, 1, 1),
        )
        _db.session.add(reminder)
        _db.session.commit()

        result = dispatch_due_reminders.delay()
        assert result.get(timeout=5) == {"dispatched": 1}


class TestSendReminder:
    def test_reminder_not_found(self, app, db):
        result = send_reminder.delay("nonexistent-id")
        data = result.get(timeout=5)
        assert data["error"] == "Reminder not found"
        assert data["reminder_id"] == "nonexistent-id"

    def test_already_sent(self, app, db):
        role = RoleRepository.find_by_name("customer")
        user = User(
            username="alreadysent",
            email="sent@test.com",
            phone_number="8888888888",
            role_id=role.id,
            is_verified=True,
        )
        user.set_password("Password123")
        _db.session.add(user)
        _db.session.commit()

        task = Task(title="Sent Task", user_id=user.id)
        _db.session.add(task)
        _db.session.commit()

        reminder = Reminder(
            task_id=task.id,
            user_id=user.id,
            reminder_time=datetime(2020, 1, 1),
            is_sent="sent",
        )
        _db.session.add(reminder)
        _db.session.commit()

        result = send_reminder.delay(reminder.id)
        data = result.get(timeout=5)
        assert data["skipped"] == "Already sent"
        assert data["reminder_id"] == reminder.id


class TestAutoStopLongRunningTimers:
    def test_no_long_running_timers(self, app, db):
        from app.jobs.tasks import auto_stop_long_running_timers
        result = auto_stop_long_running_timers.delay()
        assert result.get(timeout=5) == {"checked": 0, "auto_stopped": 0}

    def test_stops_long_running_timers(self, app, db):
        from datetime import datetime, timedelta, UTC
        from app.features.tasks.models import Task
        from app.features.time_tracking.models import TimeEntry, TimeEntryTask
        from app.jobs.tasks import auto_stop_long_running_timers

        role = RoleRepository.find_by_name("customer")
        user = User(
            username="timertest",
            email="timer@test.com",
            phone_number="7777777777",
            role_id=role.id,
            is_verified=True,
        )
        user.set_password("Password123")
        _db.session.add(user)
        _db.session.commit()

        task = Task(title="Timer Task", user_id=user.id)
        _db.session.add(task)
        _db.session.commit()

        entry = TimeEntry(
            user_id=user.id,
            started_at=datetime.now(UTC) - timedelta(hours=30),
            running=True,
        )
        _db.session.add(entry)
        _db.session.commit()
        _db.session.add(
            TimeEntryTask(
                time_entry_id=entry.id,
                task_id=task.id,
                task_title=task.title,
                position=0,
            )
        )
        _db.session.commit()

        result = auto_stop_long_running_timers.delay()
        assert result.get(timeout=5)["auto_stopped"] == 1

        refreshed = TimeEntry.query.get(entry.id)
        assert refreshed.running is False
        assert refreshed.duration_seconds == 30 * 3600

    def test_recent_timer_not_stopped(self, app, db):
        from datetime import datetime, timedelta, UTC
        from app.features.tasks.models import Task
        from app.features.time_tracking.models import TimeEntry
        from app.jobs.tasks import auto_stop_long_running_timers

        role = RoleRepository.find_by_name("customer")
        user = User(
            username="timertest2",
            email="timer2@test.com",
            phone_number="6666666666",
            role_id=role.id,
            is_verified=True,
        )
        user.set_password("Password123")
        _db.session.add(user)
        _db.session.commit()

        task = Task(title="Timer Task", user_id=user.id)
        _db.session.add(task)
        _db.session.commit()

        entry = TimeEntry(
            user_id=user.id,
            started_at=datetime.now(UTC) - timedelta(hours=1),
            running=True,
        )
        _db.session.add(entry)
        _db.session.commit()

        result = auto_stop_long_running_timers.delay()
        assert result.get(timeout=5) == {"checked": 0, "auto_stopped": 0}
        assert TimeEntry.query.get(entry.id).running is True
