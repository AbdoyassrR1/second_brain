#!/usr/bin/python3
"""Tasks service for business logic."""

from datetime import datetime
from app.shared.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.shared.logging.audit_log import (
    log_task_create, log_task_delete, log_task_complete,
    log_task_archived, log_task_restored, log_task_soft_deleted, log_task_recovered,
)
from app.shared.metrics import (
    tasks_created_total, tasks_completed_total, tasks_deleted_total,
)
from .repository import TaskRepository


# Valid status transitions as a mapping of current_status -> allowed next statuses
_VALID_STATUS_TRANSITIONS = {
    "todo": {"in_progress", "completed", "cancelled"},
    "in_progress": {"todo", "completed", "cancelled"},
    "completed": {"todo", "cancelled"},
    "cancelled": {"todo", "in_progress"},
}


def _validate_status_transition(current_status, new_status):
    """Validate if a status transition is allowed.

    Args:
        current_status: The current status of the task.
        new_status: The requested new status.

    Raises:
        ValidationError: If the transition is not allowed.
    """
    if current_status == new_status:
        return
    allowed = _VALID_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Invalid status transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {', '.join(sorted(allowed))}"
        )


class TaskService:
    """Service for task management."""

    def __init__(self):
        self.repository = TaskRepository()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _guard_ownership(self, task_id, user_id):
        """Fetch a task and ensure the requesting user owns it.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Task object

        Raises:
            NotFoundError: If task not found
            ForbiddenError: If user doesn't own the task
        """
        task = self.repository.find_by_id(task_id)
        if not task:
            raise NotFoundError("Task not found")
        if task.user_id != user_id:
            raise ForbiddenError("You do not have permission to access this task")
        return task

    def _guard_active_ownership(self, task_id, user_id):
        """Fetch a non-deleted task and ensure ownership."""
        task = self.repository.find_active_by_id(task_id)
        if not task:
            raise NotFoundError("Task not found")
        if task.user_id != user_id:
            raise ForbiddenError("You do not have permission to access this task")
        return task

    # ── Create ──────────────────────────────────────────────────────────

    def create_task(self, user_id, title, **kwargs):
        """Create a new task for a user.

        Args:
            user_id: User ID
            title: Task title
            **kwargs: Additional task fields

        Returns:
            Task object
        """
        task = self.repository.create(user_id, title, **kwargs)
        log_task_create(user_id, task.id)
        tasks_created_total.inc()
        return task

    # ── Read ────────────────────────────────────────────────────────────

    def get_task(self, task_id, user_id):
        """Get a task by ID, ensuring user owns it and it's not soft-deleted.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Task object
        """
        return self._guard_active_ownership(task_id, user_id)

    def list_tasks(
        self,
        user_id,
        status=None,
        priority=None,
        project_id=None,
        parent_task_id=None,
        due=None,
        overdue=None,
        q=None,
        labels=None,
        include_archived=None,
        archived=None,
        sort=None,
        page=1,
        page_size=20,
    ):
        """List tasks for a user with advanced filtering, sorting, pagination.

        Args:
            user_id: User ID
            status: Filter by status
            priority: Filter by priority
            project_id: Filter by project ID
            parent_task_id: Filter by parent task ID
            due: Due date filter (today, tomorrow, upcoming)
            overdue: Filter overdue tasks
            q: Search query
            labels: Filter by label IDs (comma-separated)
            include_archived: Include archived tasks
            archived: Show only archived tasks
            sort: Sort specification
            page: Page number
            page_size: Items per page

        Returns:
            tuple: (list of Task objects, total count)
        """
        return self.repository.find_by_user_id(
            user_id,
            status=status,
            priority=priority,
            project_id=project_id,
            parent_task_id=parent_task_id,
            due=due,
            overdue=overdue,
            q=q,
            labels=labels,
            include_archived=include_archived,
            archived=archived,
            sort=sort,
            page=page,
            page_size=page_size,
        )

    # ── Update ──────────────────────────────────────────────────────────

    def update_task(self, task_id, user_id, **kwargs):
        """Update a task, ensuring user owns it and transitions are valid.

        Args:
            task_id: Task ID
            user_id: Current user ID
            **kwargs: Fields to update

        Returns:
            Updated Task object
        """
        task = self._guard_active_ownership(task_id, user_id)

        new_status = kwargs.get("status")
        if new_status:
            _validate_status_transition(task.status, new_status)

            # Auto-set or clear completed_at based on status
            if new_status == "completed":
                kwargs["completed_at"] = datetime.utcnow()
            elif task.status == "completed" and new_status != "completed":
                # Reopening a completed task
                kwargs["completed_at"] = None

        updated_task = self.repository.update(task_id, **kwargs)
        return updated_task

    # ── Delete (Soft Delete) ────────────────────────────────────────────

    def delete_task(self, task_id, user_id):
        """Soft delete a task (set is_deleted=True).

        Args:
            task_id: Task ID
            user_id: Current user ID

        Raises:
            NotFoundError: If task not found
            ForbiddenError: If user doesn't own the task
        """
        self._guard_active_ownership(task_id, user_id)
        self.repository.soft_delete(task_id)
        log_task_soft_deleted(user_id, task_id)
        tasks_deleted_total.inc()

    def restore_task(self, task_id, user_id):
        """Restore a soft-deleted task.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Restored Task object
        """
        task = self._guard_ownership(task_id, user_id)
        if not task.is_deleted:
            raise ValidationError("Task is not deleted")
        self.repository.restore(task_id)
        log_task_recovered(user_id, task_id)
        return self.repository.find_by_id(task_id)

    # ── Completion workflow ─────────────────────────────────────────────

    def mark_completed(self, task_id, user_id):
        """Mark a task as completed.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Updated Task object

        Raises:
            NotFoundError: If task not found
            ForbiddenError: If user doesn't own the task
        """
        task = self._guard_active_ownership(task_id, user_id)

        if task.status == "completed":
            return task

        updated_task = self.repository.update(
            task_id, status="completed", completed_at=datetime.utcnow()
        )
        log_task_complete(user_id, task_id)
        tasks_completed_total.inc()
        return updated_task

    # ── Archive workflow ────────────────────────────────────────────────

    def archive_task(self, task_id, user_id):
        """Archive a task.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Updated Task object
        """
        self._guard_active_ownership(task_id, user_id)
        self.repository.archive(task_id)
        log_task_archived(user_id, task_id)
        return self.repository.find_by_id(task_id)

    def restore_archive_task(self, task_id, user_id):
        """Restore a task from archive.

        Args:
            task_id: Task ID
            user_id: Current user ID

        Returns:
            Updated Task object
        """
        task = self._guard_active_ownership(task_id, user_id)
        if not task.is_archived:
            raise ValidationError("Task is not archived")
        self.repository.restore_archive(task_id)
        log_task_restored(user_id, task_id)
        return self.repository.find_by_id(task_id)

    # ── Subtasks ────────────────────────────────────────────────────────

    def get_subtasks(self, task_id, user_id):
        """Get subtasks for a parent task, ensuring ownership.

        Args:
            task_id: Parent task ID
            user_id: Current user ID

        Returns:
            List of Task objects
        """
        self._guard_active_ownership(task_id, user_id)
        return self.repository.get_subtasks(task_id)

    # ── Bulk Operations ─────────────────────────────────────────────────

    def bulk_complete(self, task_ids, user_id):
        """Bulk complete tasks."""
        return self.repository.bulk_complete(task_ids, user_id)

    def bulk_archive(self, task_ids, user_id):
        """Bulk archive tasks."""
        return self.repository.bulk_archive(task_ids, user_id)

    def bulk_restore_archive(self, task_ids, user_id):
        """Bulk restore archived tasks."""
        return self.repository.bulk_restore_archive(task_ids, user_id)

    def bulk_soft_delete(self, task_ids, user_id):
        """Bulk soft delete tasks."""
        return self.repository.bulk_soft_delete(task_ids, user_id)

    def bulk_restore(self, task_ids, user_id):
        """Bulk restore soft-deleted tasks."""
        return self.repository.bulk_restore(task_ids, user_id)

    def bulk_update(self, task_ids, user_id, **kwargs):
        """Bulk update tasks."""
        return self.repository.bulk_update(task_ids, user_id, **kwargs)

    # ── Statistics ──────────────────────────────────────────────────────

    def get_statistics(self, user_id):
        """Get task statistics for a user.

        Args:
            user_id: User ID

        Returns:
            dict: Statistics data
        """
        return self.repository.get_statistics(user_id)