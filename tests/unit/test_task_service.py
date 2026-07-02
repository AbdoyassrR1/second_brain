"""Tests for task service business logic."""

import pytest
from datetime import date

from app.features.tasks.service import TaskService, _validate_status_transition
from app.shared.exceptions import NotFoundError, ForbiddenError, ValidationError


class TestTaskCreate:
    """Test task creation through service."""

    def test_create_task_success(self, db, verified_user):
        """Test successful task creation."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id,
            title="Test Task",
            description="A test task description",
            priority="medium",
        )

        assert task is not None
        assert task.title == "Test Task"
        assert task.description == "A test task description"
        assert task.user_id == verified_user.id
        assert task.status == "todo"
        assert task.priority == "medium"

    def test_create_task_with_all_fields(self, db, verified_user):
        """Test task creation with all optional fields."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id,
            title="Full Task",
            description="Full description",
            priority="high",
            status="in_progress",
            due_date=date(2026, 12, 31),
        )

        assert task.title == "Full Task"
        assert task.description == "Full description"
        assert task.priority == "high"
        assert task.status == "in_progress"
        assert task.due_date == date(2026, 12, 31)


class TestTaskRead:
    """Test task retrieval through service."""

    def test_get_task_success(self, db, verified_user):
        """Test getting a task by ID."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id,
            title="Task to Get",
        )

        retrieved = service.get_task(task.id, verified_user.id)
        assert retrieved.id == task.id
        assert retrieved.title == "Task to Get"

    def test_get_task_not_found(self, db, verified_user):
        """Test getting a non-existent task raises error."""
        service = TaskService()
        with pytest.raises(NotFoundError):
            service.get_task("nonexistent-id", verified_user.id)

    def test_get_task_forbidden(self, db, verified_user, test_user_id):
        """Test getting another user's task raises ForbiddenError."""
        service = TaskService()

        # Create task as verified_user
        task = service.create_task(
            user_id=verified_user.id,
            title="Other User's Task",
        )

        # Try to get it as a different user (using a different ID)
        with pytest.raises(ForbiddenError):
            service.get_task(task.id, "other-user-id")

    def test_list_tasks(self, db, verified_user):
        """Test listing tasks for a user."""
        service = TaskService()

        # Create multiple tasks
        for i in range(3):
            service.create_task(
                user_id=verified_user.id,
                title=f"Task {i}",
                priority="low" if i % 2 == 0 else "high",
            )

        tasks, total = service.list_tasks(verified_user.id)
        assert len(tasks) == 3
        assert total == 3

    def test_list_tasks_with_status_filter(self, db, verified_user):
        """Test listing tasks filtered by status."""
        service = TaskService()

        service.create_task(
            user_id=verified_user.id, title="Todo Task", status="todo"
        )
        service.create_task(
            user_id=verified_user.id, title="In Progress Task", status="in_progress"
        )
        service.create_task(
            user_id=verified_user.id, title="Completed Task", status="completed"
        )

        todo_tasks, total = service.list_tasks(verified_user.id, status="todo")
        assert len(todo_tasks) == 1
        assert total == 1
        assert todo_tasks[0].title == "Todo Task"

    def test_list_tasks_with_priority_filter(self, db, verified_user):
        """Test listing tasks filtered by priority."""
        service = TaskService()

        service.create_task(
            user_id=verified_user.id, title="Low Priority", priority="low"
        )
        service.create_task(
            user_id=verified_user.id, title="High Priority", priority="high"
        )

        high_tasks, total = service.list_tasks(verified_user.id, priority="high")
        assert len(high_tasks) == 1
        assert total == 1
        assert high_tasks[0].title == "High Priority"

    def test_list_tasks_pagination(self, db, verified_user):
        """Test listing tasks with page and page_size."""
        service = TaskService()

        for i in range(5):
            service.create_task(
                user_id=verified_user.id, title=f"Task {i}"
            )

        first_page, total = service.list_tasks(verified_user.id, page=1, page_size=2)
        assert len(first_page) == 2
        assert total == 5

        second_page, total2 = service.list_tasks(verified_user.id, page=2, page_size=2)
        assert len(second_page) == 2
        assert total2 == 5

        # Ensure they're different tasks
        assert first_page[0].id != second_page[0].id


class TestTaskUpdate:
    """Test task update through service."""

    def test_update_task_title(self, db, verified_user):
        """Test updating a task's title."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Original Title"
        )

        updated = service.update_task(task.id, verified_user.id, title="Updated Title")
        assert updated.title == "Updated Title"

    def test_update_task_status_valid_transition(self, db, verified_user):
        """Test valid status transitions."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Status Task"
        )

        updated = service.update_task(task.id, verified_user.id, status="in_progress")
        assert updated.status == "in_progress"

        updated = service.update_task(task.id, verified_user.id, status="completed")
        assert updated.status == "completed"

    def test_update_task_status_invalid_transition(self, db, verified_user):
        """Test invalid status transition raises error."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Status Task"
        )

        # Cannot go directly from 'todo' to 'cancelled' should fail... actually it is allowed
        # Let's test: completed -> todo is allowed per _VALID_STATUS_TRANSITIONS
        service.update_task(task.id, verified_user.id, status="completed")
        # Completed -> in_progress is NOT allowed
        with pytest.raises(ValidationError):
            service.update_task(task.id, verified_user.id, status="in_progress")

    def test_update_task_completed_sets_completed_at(self, db, verified_user):
        """Test completing a task sets completed_at."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Complete Me"
        )

        updated = service.update_task(task.id, verified_user.id, status="completed")
        assert updated.status == "completed"
        assert updated.completed_at is not None

    def test_update_task_reopen_clears_completed_at(self, db, verified_user):
        """Test reopening a completed task clears completed_at."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Reopen Me"
        )

        # Complete it first
        service.update_task(task.id, verified_user.id, status="completed")
        # Reopen it
        updated = service.update_task(task.id, verified_user.id, status="todo")
        assert updated.status == "todo"
        assert updated.completed_at is None

    def test_update_task_forbidden(self, db, verified_user):
        """Test updating another user's task raises error."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Not Yours"
        )

        with pytest.raises(ForbiddenError):
            service.update_task(task.id, "other-user-id", title="Hacked")


class TestTaskDelete:
    """Test task deletion through service."""

    def test_delete_task_success(self, db, verified_user):
        """Test successful task deletion (soft delete)."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Delete Me"
        )

        service.delete_task(task.id, verified_user.id)

        # After soft delete, the task still exists but is marked as deleted
        # get_task (via _guard_active_ownership) should now raise NotFoundError
        # since the task is soft-deleted
        with pytest.raises(NotFoundError):
            service.get_task(task.id, verified_user.id)

        # But we can still find it via _guard_ownership (get_task uses old method)
        # Let's verify the task was soft-deleted by checking directly
        from app.features.tasks.models import Task
        from app.extensions import db
        soft_deleted_task = Task.query.filter_by(id=task.id).first()
        assert soft_deleted_task is not None
        assert soft_deleted_task.is_deleted is True
        assert soft_deleted_task.deleted_at is not None

    def test_delete_task_forbidden(self, db, verified_user):
        """Test deleting another user's task raises error."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Not Yours"
        )

        with pytest.raises(ForbiddenError):
            service.delete_task(task.id, "other-user-id")

    def test_delete_task_not_found(self, db, verified_user):
        """Test deleting a non-existent task raises error."""
        service = TaskService()
        with pytest.raises(NotFoundError):
            service.delete_task("nonexistent-id", verified_user.id)


class TestCompletionWorkflow:
    """Test task completion workflow."""

    def test_mark_completed(self, db, verified_user):
        """Test marking a task as completed."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Complete Me"
        )

        completed = service.mark_completed(task.id, verified_user.id)
        assert completed.status == "completed"
        assert completed.completed_at is not None

    def test_mark_already_completed_is_idempotent(self, db, verified_user):
        """Test marking an already completed task doesn't error."""
        service = TaskService()
        task = service.create_task(
            user_id=verified_user.id, title="Already Done"
        )

        first = service.mark_completed(task.id, verified_user.id)
        second = service.mark_completed(task.id, verified_user.id)
        assert first.completed_at == second.completed_at


class TestStatusTransitions:
    """Test status transition validation."""

    def test_valid_transitions(self):
        """Test all valid transitions pass."""
        # These should not raise
        _validate_status_transition("todo", "in_progress")
        _validate_status_transition("todo", "completed")
        _validate_status_transition("todo", "cancelled")
        _validate_status_transition("in_progress", "todo")
        _validate_status_transition("in_progress", "completed")
        _validate_status_transition("in_progress", "cancelled")
        _validate_status_transition("completed", "todo")
        _validate_status_transition("completed", "cancelled")
        _validate_status_transition("cancelled", "todo")
        _validate_status_transition("cancelled", "in_progress")

    def test_same_status_is_valid(self):
        """Test that staying in the same status is always valid."""
        _validate_status_transition("todo", "todo")
        _validate_status_transition("completed", "completed")

    def test_invalid_transitions(self):
        """Test invalid transitions raise ValidationError."""
        with pytest.raises(ValidationError):
            _validate_status_transition("completed", "in_progress")
        with pytest.raises(ValidationError):
            _validate_status_transition("cancelled", "completed")