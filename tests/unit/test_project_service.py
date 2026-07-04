#!/usr/bin/python3
"""Tests for project service business logic."""

import pytest
from app.features.projects.service import ProjectService
from app.shared.exceptions import NotFoundError, ForbiddenError
from app.shared.exceptions import ValidationError as AppValidationError


class TestProjectCreate:
    """Test project creation through service."""

    def test_create_project_success(self, db, verified_user):
        """Test successful project creation."""
        service = ProjectService()
        project = service.create_project(
            verified_user.id, name="My Project", description="A new project", color="#00FF00"
        )

        assert project is not None
        assert project.name == "My Project"
        assert project.description == "A new project"
        assert project.color == "#00FF00"
        assert project.user_id == verified_user.id

    def test_create_project_without_optional(self, db, verified_user):
        """Test project creation with only required fields."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Minimal")

        assert project.name == "Minimal"
        assert project.description is None
        assert project.color is None


class TestProjectRead:
    """Test project retrieval through service."""

    def test_get_project_success(self, db, verified_user):
        """Test getting a project by ID."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="My Project")

        retrieved = service.get_project(project.id, verified_user.id)
        assert retrieved.id == project.id
        assert retrieved.name == "My Project"

    def test_get_project_not_found(self, db, verified_user):
        """Test getting a non-existent project raises error."""
        service = ProjectService()
        with pytest.raises(NotFoundError):
            service.get_project("nonexistent-id", verified_user.id)

    def test_get_project_forbidden(self, db, verified_user):
        """Test getting another user's project raises ForbiddenError."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Private")

        with pytest.raises(ForbiddenError):
            service.get_project(project.id, "other-user-id")

    def test_list_projects_empty(self, db, verified_user):
        """Test listing projects when none exist."""
        service = ProjectService()
        projects = service.list_projects(verified_user.id)
        assert len(projects) == 0

    def test_list_projects_with_data(self, db, verified_user):
        """Test listing projects after creating some."""
        service = ProjectService()
        service.create_project(verified_user.id, name="Work")
        service.create_project(verified_user.id, name="Personal")

        projects = service.list_projects(verified_user.id)
        assert len(projects) == 2

    def test_list_projects_user_isolation(self, db, verified_user):
        """Test projects are isolated per user."""
        service = ProjectService()
        service.create_project(verified_user.id, name="Secret")

        other_projects = service.list_projects("other-user-id")
        assert len(other_projects) == 0


class TestProjectUpdate:
    """Test project update through service."""

    def test_update_project_success(self, db, verified_user):
        """Test successful project update."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Old Name")

        updated = service.update_project(project.id, verified_user.id, name="New Name", description="Updated desc")
        assert updated.name == "New Name"
        assert updated.description == "Updated desc"

    def test_update_project_not_found(self, db, verified_user):
        """Test updating a non-existent project raises error."""
        service = ProjectService()
        with pytest.raises(NotFoundError):
            service.update_project("nonexistent", verified_user.id, name="New")

    def test_update_project_forbidden(self, db, verified_user):
        """Test updating another user's project raises error."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Not Yours")

        with pytest.raises(ForbiddenError):
            service.update_project(project.id, "other-user-id", name="Hacked")


class TestProjectDelete:
    """Test project deletion through service."""

    def test_delete_project_success(self, db, verified_user):
        """Test successful project deletion."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Temp")

        service.delete_project(project.id, verified_user.id)

        projects = service.list_projects(verified_user.id)
        assert len(projects) == 0

    def test_delete_project_not_found(self, db, verified_user):
        """Test deleting a non-existent project raises error."""
        service = ProjectService()
        with pytest.raises(NotFoundError):
            service.delete_project("nonexistent", verified_user.id)

    def test_delete_project_forbidden(self, db, verified_user):
        """Test deleting another user's project raises error."""
        service = ProjectService()
        project = service.create_project(verified_user.id, name="Not Yours")

        with pytest.raises(ForbiddenError):
            service.delete_project(project.id, "other-user-id")
