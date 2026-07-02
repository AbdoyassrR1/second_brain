#!/usr/bin/python3
"""Labels service for business logic."""

from app.shared.exceptions import NotFoundError, ForbiddenError
from app.shared.logging.audit_log import log_label_create, log_label_delete, log_label_assigned, log_label_removed
from app.shared.metrics import labels_created_total, labels_deleted_total
from .repository import LabelRepository
from app.features.tasks.repository import TaskRepository


class LabelService:
    """Service for label management."""

    def __init__(self):
        self.repository = LabelRepository()
        self.task_repository = TaskRepository()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _guard_ownership(self, label_id, user_id):
        """Fetch a label and ensure the requesting user owns it.

        Args:
            label_id: Label ID
            user_id: Current user ID

        Returns:
            Label object

        Raises:
            NotFoundError: If label not found
            ForbiddenError: If user doesn't own the label
        """
        label = self.repository.find_by_id(label_id)
        if not label:
            raise NotFoundError("Label not found")
        if label.user_id != user_id:
            raise ForbiddenError("You do not have permission to access this label")
        return label

    def _guard_task_ownership(self, task_id, user_id):
        """Fetch a task and ensure the requesting user owns it."""
        task = self.task_repository.find_by_id(task_id)
        if not task:
            raise NotFoundError("Task not found")
        if task.user_id != user_id:
            raise ForbiddenError("You do not have permission to access this task")
        return task

    # ── Create ──────────────────────────────────────────────────────────

    def create_label(self, user_id, name, **kwargs):
        """Create a new label for a user.

        Args:
            user_id: User ID
            name: Label name
            **kwargs: Additional label fields

        Returns:
            Label object
        """
        label = self.repository.create(user_id, name, **kwargs)
        log_label_create(user_id, label.id)
        labels_created_total.inc()
        return label

    # ── Read ────────────────────────────────────────────────────────────

    def list_labels(self, user_id):
        """List labels for a user.

        Args:
            user_id: User ID

        Returns:
            List of Label objects
        """
        return self.repository.find_by_user_id(user_id)

    # ── Delete ──────────────────────────────────────────────────────────

    def delete_label(self, label_id, user_id):
        """Delete a label, ensuring user owns it.

        Args:
            label_id: Label ID
            user_id: Current user ID

        Raises:
            NotFoundError: If label not found
            ForbiddenError: If user doesn't own the label
        """
        self._guard_ownership(label_id, user_id)
        self.repository.delete(label_id)
        log_label_delete(user_id, label_id)
        labels_deleted_total.inc()

    # ── Label Assignment ────────────────────────────────────────────────

    def assign_label_to_task(self, task_id, label_id, user_id):
        """Assign a label to a task.

        Args:
            task_id: Task ID
            label_id: Label ID
            user_id: Current user ID

        Returns:
            Updated Task object
        """
        task = self._guard_task_ownership(task_id, user_id)
        label = self._guard_ownership(label_id, user_id)

        if label not in task.labels:
            task.labels.append(label)
            from app.extensions import db
            db.session.commit()
            log_label_assigned(user_id, task_id, label_id)

        return task

    def remove_label_from_task(self, task_id, label_id, user_id):
        """Remove a label from a task.

        Args:
            task_id: Task ID
            label_id: Label ID
            user_id: Current user ID

        Returns:
            Updated Task object
        """
        task = self._guard_task_ownership(task_id, user_id)
        label = self._guard_ownership(label_id, user_id)

        if label in task.labels:
            task.labels.remove(label)
            from app.extensions import db
            db.session.commit()
            log_label_removed(user_id, task_id, label_id)

        return task