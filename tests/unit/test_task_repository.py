#!/usr/bin/python3
"""Tests for task repository."""

import pytest
from datetime import date, datetime, timedelta
from app.features.tasks.repository import TaskRepository
from app.features.tasks.models import Task


class TestTaskRepository:
    """Test TaskRepository."""

    def test_create_task(self, db, verified_user):
        """Test creating a task."""
        task = TaskRepository.create(
            verified_user.id, title="Test Task", description="Desc", priority="high"
        )
        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "Desc"
        assert task.priority == "high"
        assert task.status == "todo"
        assert task.user_id == verified_user.id

    def test_find_by_id(self, db, verified_user):
        """Test finding a task by ID."""
        task = TaskRepository.create(verified_user.id, title="Find Me")

        found = TaskRepository.find_by_id(task.id)
        assert found is not None
        assert found.id == task.id

    def test_find_by_id_not_found(self, db):
        """Test finding a non-existent task."""
        found = TaskRepository.find_by_id("nonexistent")
        assert found is None

    def test_find_active_by_id(self, db, verified_user):
        """Test finding only active (non-deleted) tasks."""
        task = TaskRepository.create(verified_user.id, title="Active Task")

        found = TaskRepository.find_active_by_id(task.id)
        assert found is not None

        TaskRepository.soft_delete(task.id)

        found = TaskRepository.find_active_by_id(task.id)
        assert found is None

    def test_find_by_user_id(self, db, verified_user):
        """Test finding tasks by user."""
        TaskRepository.create(verified_user.id, title="Task 1")
        TaskRepository.create(verified_user.id, title="Task 2")

        p = TaskRepository.find_by_user_id(verified_user.id)
        assert p.total == 2
        assert len(p.items) == 2

    def test_find_by_user_id_pagination(self, db, verified_user):
        """Test pagination in find_by_user_id."""
        for i in range(5):
            TaskRepository.create(verified_user.id, title=f"Task {i}")

        p = TaskRepository.find_by_user_id(verified_user.id, page=1, per_page=2)
        assert p.total == 5
        assert len(p.items) == 2

    def test_find_by_user_id_status_filter(self, db, verified_user):
        """Test status filter in find_by_user_id."""
        TaskRepository.create(verified_user.id, title="Todo", status="todo")
        TaskRepository.create(verified_user.id, title="Completed", status="completed")

        p = TaskRepository.find_by_user_id(verified_user.id, status="completed")
        assert p.total == 1
        assert p.items[0].title == "Completed"

    def test_find_by_user_id_priority_filter(self, db, verified_user):
        """Test priority filter."""
        TaskRepository.create(verified_user.id, title="High", priority="high")
        TaskRepository.create(verified_user.id, title="Low", priority="low")

        p = TaskRepository.find_by_user_id(verified_user.id, priority="high")
        assert p.total == 1

    def test_find_by_user_id_search(self, db, verified_user):
        """Test search query."""
        TaskRepository.create(verified_user.id, title="Special Project")
        TaskRepository.create(verified_user.id, title="Other Task")

        p = TaskRepository.find_by_user_id(verified_user.id, q="Special")
        assert p.total == 1

    def test_update_task(self, db, verified_user):
        """Test updating a task."""
        task = TaskRepository.create(verified_user.id, title="Original")

        updated = TaskRepository.update(task.id, title="Updated", priority="urgent")
        assert updated.title == "Updated"
        assert updated.priority == "urgent"

    def test_soft_delete_and_restore(self, db, verified_user):
        """Test soft deleting and restoring a task."""
        task = TaskRepository.create(verified_user.id, title="To Delete")

        TaskRepository.soft_delete(task.id)
        deleted = TaskRepository.find_by_id(task.id)
        assert deleted.is_deleted is True
        assert deleted.deleted_at is not None

        TaskRepository.restore(task.id)
        restored = TaskRepository.find_by_id(task.id)
        assert restored.is_deleted is False
        assert restored.deleted_at is None

    def test_archive_and_restore(self, db, verified_user):
        """Test archiving and restoring a task."""
        task = TaskRepository.create(verified_user.id, title="To Archive")

        TaskRepository.archive(task.id)
        archived = TaskRepository.find_by_id(task.id)
        assert archived.is_archived is True

        TaskRepository.restore_archive(task.id)
        restored = TaskRepository.find_by_id(task.id)
        assert restored.is_archived is False

    def test_get_statistics(self, db, verified_user):
        """Test getting task statistics."""
        TaskRepository.create(verified_user.id, title="Todo Task", status="todo")
        TaskRepository.create(verified_user.id, title="Done Task", status="completed")

        stats = TaskRepository.get_statistics(verified_user.id)
        assert stats["total_tasks"] == 2
        assert stats["active_tasks"] == 1
        assert stats["completed_tasks"] == 1
        assert stats["completion_rate"] == 50.0

    def test_bulk_complete(self, db, verified_user):
        """Test bulk completing tasks."""
        t1 = TaskRepository.create(verified_user.id, title="Task 1")
        t2 = TaskRepository.create(verified_user.id, title="Task 2")

        TaskRepository.bulk_complete([t1.id, t2.id], verified_user.id)

        assert TaskRepository.find_by_id(t1.id).status == "completed"
        assert TaskRepository.find_by_id(t2.id).status == "completed"

    def test_bulk_archive_and_restore(self, db, verified_user):
        """Test bulk archive and restore."""
        t1 = TaskRepository.create(verified_user.id, title="Task 1")
        t2 = TaskRepository.create(verified_user.id, title="Task 2")

        TaskRepository.bulk_archive([t1.id, t2.id], verified_user.id)
        assert TaskRepository.find_by_id(t1.id).is_archived is True

        TaskRepository.bulk_restore_archive([t1.id, t2.id], verified_user.id)
        assert TaskRepository.find_by_id(t1.id).is_archived is False

    def test_bulk_soft_delete_and_restore(self, db, verified_user):
        """Test bulk soft delete and restore."""
        t1 = TaskRepository.create(verified_user.id, title="Task 1")
        t2 = TaskRepository.create(verified_user.id, title="Task 2")

        TaskRepository.bulk_soft_delete([t1.id, t2.id], verified_user.id)
        assert TaskRepository.find_by_id(t1.id).is_deleted is True

        TaskRepository.bulk_restore([t1.id, t2.id], verified_user.id)
        assert TaskRepository.find_by_id(t1.id).is_deleted is False

    def test_bulk_update(self, db, verified_user):
        """Test bulk updating tasks."""
        t1 = TaskRepository.create(verified_user.id, title="Task 1", priority="low")
        t2 = TaskRepository.create(verified_user.id, title="Task 2", priority="low")

        TaskRepository.bulk_update([t1.id, t2.id], verified_user.id, priority="high")

        assert TaskRepository.find_by_id(t1.id).priority == "high"
        assert TaskRepository.find_by_id(t2.id).priority == "high"
