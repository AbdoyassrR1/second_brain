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
