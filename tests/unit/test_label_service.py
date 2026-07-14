#!/usr/bin/python3
"""Tests for label service business logic."""

import pytest
from app.features.labels.service import LabelService
from app.shared.exceptions import NotFoundError, ForbiddenError


class TestLabelCreate:
    """Test label creation through service."""

    def test_create_label_success(self, db, verified_user):
        """Test successful label creation."""
        service = LabelService()
        label = service.create_label(verified_user.id, name="urgent", color="#FF0000")

        assert label is not None
        assert label.name == "urgent"
        assert label.color == "#FF0000"
        assert label.user_id == verified_user.id

    def test_create_label_without_color(self, db, verified_user):
        """Test label creation without optional color."""
        service = LabelService()
        label = service.create_label(verified_user.id, name="general")

        assert label.name == "general"
        assert label.color is None


class TestLabelList:
    """Test label listing through service."""

    def test_list_labels_empty(self, db, verified_user):
        """Test listing labels when none exist."""
        service = LabelService()
        p = service.list_labels(verified_user.id)
        assert len(p.items) == 0
        assert p.total == 0

    def test_list_labels_with_data(self, db, verified_user):
        """Test listing labels after creating some."""
        service = LabelService()
        service.create_label(verified_user.id, name="urgent")
        service.create_label(verified_user.id, name="bug")
        service.create_label(verified_user.id, name="feature")

        p = service.list_labels(verified_user.id)
        assert len(p.items) == 3
        assert p.total == 3

    def test_list_labels_other_user_isolation(self, db, verified_user):
        """Test labels are isolated per user."""
        service = LabelService()
        service.create_label(verified_user.id, name="private-label")

        # A different user ID should see no labels
        p = service.list_labels("other-user-id")
        assert len(p.items) == 0
        assert p.total == 0


class TestLabelDelete:
    """Test label deletion through service."""

    def test_delete_label_success(self, db, verified_user):
        """Test successful label deletion."""
        service = LabelService()
        label = service.create_label(verified_user.id, name="temporary")

        service.delete_label(label.id, verified_user.id)

        p = service.list_labels(verified_user.id)
        assert len(p.items) == 0
        assert p.total == 0

    def test_delete_label_not_found(self, db, verified_user):
        """Test deleting a non-existent label raises error."""
        service = LabelService()
        with pytest.raises(NotFoundError):
            service.delete_label("nonexistent-id", verified_user.id)

    def test_delete_label_forbidden(self, db, verified_user):
        """Test deleting another user's label raises ForbiddenError."""
        service = LabelService()
        label = service.create_label(verified_user.id, name="not-yours")

        with pytest.raises(ForbiddenError):
            service.delete_label(label.id, "other-user-id")


class TestLabelAssignment:
    """Test label assignment to tasks."""

    def test_assign_label_to_task(self, db, verified_user):
        """Test assigning a label to a task."""
        from app.features.tasks.service import TaskService

        label_service = LabelService()
        task_service = TaskService()

        label = label_service.create_label(verified_user.id, name="urgent")
        task = task_service.create_task(verified_user.id, title="Important Task")

        updated_task = label_service.assign_label_to_task(task.id, label.id, verified_user.id)
        assert label in updated_task.labels

    def test_assign_label_idempotent(self, db, verified_user):
        """Test assigning the same label twice is idempotent."""
        from app.features.tasks.service import TaskService

        label_service = LabelService()
        task_service = TaskService()

        label = label_service.create_label(verified_user.id, name="bug")
        task = task_service.create_task(verified_user.id, title="Bug Task")

        label_service.assign_label_to_task(task.id, label.id, verified_user.id)
        label_service.assign_label_to_task(task.id, label.id, verified_user.id)

        from app.extensions import db as _db
        _db.session.refresh(task)
        assert task.labels.count(label) == 1

    def test_remove_label_from_task(self, db, verified_user):
        """Test removing a label from a task."""
        from app.features.tasks.service import TaskService

        label_service = LabelService()
        task_service = TaskService()

        label = label_service.create_label(verified_user.id, name="wontfix")
        task = task_service.create_task(verified_user.id, title="Skipped Task")
        label_service.assign_label_to_task(task.id, label.id, verified_user.id)

        updated_task = label_service.remove_label_from_task(task.id, label.id, verified_user.id)
        assert label not in updated_task.labels

    def test_assign_label_to_task_forbidden(self, db, verified_user):
        """Test assigning label to another user's task raises error."""
        from app.features.tasks.service import TaskService

        label_service = LabelService()
        task_service = TaskService()

        label = label_service.create_label(verified_user.id, name="personal")
        task = task_service.create_task(verified_user.id, title="My Task")

        with pytest.raises(ForbiddenError):
            label_service.assign_label_to_task(task.id, label.id, "other-user-id")

    def test_assign_label_to_task_not_found(self, db, verified_user):
        """Test assigning a non-existent label raises error."""
        from app.features.tasks.service import TaskService

        label_service = LabelService()
        task_service = TaskService()

        task = task_service.create_task(verified_user.id, title="Task")

        with pytest.raises(NotFoundError):
            label_service.assign_label_to_task(task.id, "nonexistent-label", verified_user.id)

