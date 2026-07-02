#!/usr/bin/python3
"""Projects repository for database operations."""

from app.extensions import db
from .models import Project


class ProjectRepository:
    """Repository for Project database operations."""

    @staticmethod
    def find_by_id(project_id):
        """Find project by ID."""
        return Project.query.filter_by(id=project_id).first()

    @staticmethod
    def find_by_user_id(user_id):
        """Find all projects for a user."""
        return Project.query.filter_by(user_id=user_id).all()

    @staticmethod
    def create(user_id, name, **kwargs):
        """Create and save a new project."""
        project = Project(user_id=user_id, name=name, **kwargs)
        db.session.add(project)
        db.session.commit()
        return project

    @staticmethod
    def update(project_id, **kwargs):
        """Update project fields."""
        project = Project.query.filter_by(id=project_id).first()
        if project and kwargs:
            for key, value in kwargs.items():
                if hasattr(project, key) and key not in ["id", "user_id", "created_at"]:
                    setattr(project, key, value)
            db.session.commit()
        return project

    @staticmethod
    def delete(project_id):
        """Delete a project."""
        project = Project.query.filter_by(id=project_id).first()
        if project:
            # Unlink tasks from this project first
            from app.features.tasks.models import Task
            Task.query.filter_by(project_id=project_id).update({"project_id": None})
            db.session.delete(project)
            db.session.commit()
            return True
        return False

    @staticmethod
    def count_by_user(user_id):
        """Count projects for a user."""
        return Project.query.filter_by(user_id=user_id).count()