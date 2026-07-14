#!/usr/bin/python3
"""Projects service for business logic."""

from app.shared.exceptions import NotFoundError, ForbiddenError
from app.shared.logging.audit_log import log_project_create, log_project_update, log_project_delete
from app.shared.metrics import projects_created_total, projects_deleted_total
from .repository import ProjectRepository


class ProjectService:
    """Service for project management."""

    def __init__(self):
        self.repository = ProjectRepository()

    # ── Helpers ─────────────────────────────────────────────────────────

    def _guard_ownership(self, project_id, user_id):
        """Fetch a project and ensure the requesting user owns it.

        Args:
            project_id: Project ID
            user_id: Current user ID

        Returns:
            Project object

        Raises:
            NotFoundError: If project not found
            ForbiddenError: If user doesn't own the project
        """
        project = self.repository.find_by_id(project_id)
        if not project:
            raise NotFoundError("Project not found")
        if project.user_id != user_id:
            raise ForbiddenError("You do not have permission to access this project")
        return project

    # ── Create ──────────────────────────────────────────────────────────

    def create_project(self, user_id, name, **kwargs):
        """Create a new project for a user.

        Args:
            user_id: User ID
            name: Project name
            **kwargs: Additional project fields

        Returns:
            Project object
        """
        project = self.repository.create(user_id, name, **kwargs)
        log_project_create(user_id, project.id)
        projects_created_total.inc()
        return project

    # ── Read ────────────────────────────────────────────────────────────

    def get_project(self, project_id, user_id):
        """Get a project by ID, ensuring user owns it.

        Args:
            project_id: Project ID
            user_id: Current user ID

        Returns:
            Project object
        """
        return self._guard_ownership(project_id, user_id)

    def list_projects(self, user_id, page=1, per_page=20):
        return self.repository.find_by_user_id(user_id, page=page, per_page=per_page)

    # ── Update ──────────────────────────────────────────────────────────

    def update_project(self, project_id, user_id, **kwargs):
        """Update a project, ensuring user owns it.

        Args:
            project_id: Project ID
            user_id: Current user ID
            **kwargs: Fields to update

        Returns:
            Updated Project object
        """
        self._guard_ownership(project_id, user_id)
        updated_project = self.repository.update(project_id, **kwargs)
        log_project_update(user_id, project_id, kwargs)
        return updated_project

    # ── Delete ──────────────────────────────────────────────────────────

    def delete_project(self, project_id, user_id):
        """Delete a project, ensuring user owns it.

        Args:
            project_id: Project ID
            user_id: Current user ID

        Raises:
            NotFoundError: If project not found
            ForbiddenError: If user doesn't own the project
        """
        self._guard_ownership(project_id, user_id)
        self.repository.delete(project_id)
        log_project_delete(user_id, project_id)
        projects_deleted_total.inc()