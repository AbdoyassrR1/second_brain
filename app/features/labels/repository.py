#!/usr/bin/python3
"""Labels repository for database operations."""

from app.extensions import db
from app.shared.database import database
from .models import Label


class LabelRepository:
    """Repository for Label database operations."""

    @staticmethod
    def find_by_id(label_id):
        """Find label by ID."""
        return Label.query.filter_by(id=label_id).first()

    @staticmethod
    def find_by_user_id(user_id, page=1, per_page=20):
        query = Label.query.filter_by(user_id=user_id)
        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def create(user_id, name, **kwargs):
        """Create and save a new label."""
        label = Label(user_id=user_id, name=name, **kwargs)
        database.add(label)
        database.commit()
        return label

    @staticmethod
    def delete(label_id):
        """Delete a label."""
        label = Label.query.filter_by(id=label_id).first()
        if label:
            database.delete(label)
            database.commit()
            return True
        return False

    @staticmethod
    def count_by_user(user_id):
        """Count labels for a user."""
        return Label.query.filter_by(user_id=user_id).count()