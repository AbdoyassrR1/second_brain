#!/usr/bin/python3
"""Tests for reminder service business logic."""

import pytest
from datetime import datetime, timedelta, UTC
from app.features.reminders.service import ReminderService
from app.shared.exceptions import NotFoundError


class TestReminderCreate:
    """Test reminder creation through service."""

    def test_create_reminder_success(self, db, verified_user):
        """Test successful reminder creation."""
        from app.features.tasks.service import TaskService
        task_service = TaskService()
        task = task_service.create_task(verified_user.id, title="Task with Reminder")

        service = ReminderService()
        future = datetime.now(UTC) + timedelta(hours=1)
        reminder = service.create_reminder(task.id, verified_user.id, future)

        assert reminder is not None
        assert reminder.task_id == task.id
        assert reminder.user_id == verified_user.id
        assert reminder.is_sent == "pending"


class TestPendingReminders:
    """Test pending reminder retrieval."""

    def test_get_pending_reminders_empty(self, db, verified_user):
        """Test no pending reminders."""
        service = ReminderService()
        pending = service.get_pending_reminders()
        assert len(pending) == 0

    def test_get_pending_reminders_with_data(self, db, verified_user):
        """Test getting pending reminders."""
        from app.features.tasks.service import TaskService
        task_service = TaskService()
        task = task_service.create_task(verified_user.id, title="Remind Me")

        service = ReminderService()
        past = datetime.now(UTC) - timedelta(minutes=5)
        service.create_reminder(task.id, verified_user.id, past)

        pending = service.get_pending_reminders()
        assert len(pending) == 1

    def test_pending_reminders_excludes_future(self, db, verified_user):
        """Test future reminders are not returned as pending."""
        from app.features.tasks.service import TaskService
        task_service = TaskService()
        task = task_service.create_task(verified_user.id, title="Future Reminder")

        service = ReminderService()
        # Use a far-future time to avoid timezone comparison issues with SQLite
        future = datetime.now(UTC) + timedelta(days=365)
        service.create_reminder(task.id, verified_user.id, future)

        pending = service.get_pending_reminders()
        assert len(pending) == 0

    def test_pending_reminders_excludes_sent(self, db, verified_user):
        """Test sent reminders are not returned."""
        from app.features.tasks.service import TaskService
        task_service = TaskService()
        task = task_service.create_task(verified_user.id, title="Sent Reminder")

        service = ReminderService()
        past = datetime.now(UTC) - timedelta(minutes=5)
        reminder = service.create_reminder(task.id, verified_user.id, past)
        service.mark_sent(reminder.id)

        pending = service.get_pending_reminders()
        assert len(pending) == 0


class TestMarkSent:
    """Test marking reminders as sent."""

    def test_mark_sent_success(self, db, verified_user):
        """Test successfully marking a reminder as sent."""
        from app.features.tasks.service import TaskService
        task_service = TaskService()
        task = task_service.create_task(verified_user.id, title="Task")

        service = ReminderService()
        future = datetime.now(UTC) + timedelta(hours=1)
        reminder = service.create_reminder(task.id, verified_user.id, future)

        updated = service.mark_sent(reminder.id)
        assert updated.is_sent == "sent"

    def test_mark_sent_not_found(self, db, verified_user):
        """Test marking a non-existent reminder raises error."""
        service = ReminderService()
        with pytest.raises(NotFoundError):
            service.mark_sent("nonexistent-id")
