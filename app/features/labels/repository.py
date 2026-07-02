#!/usr/bin/python3
"""Labels repository for database operations."""

from app.extensions import db
from .models import Label


class LabelRepository:
    """Repository for Label database operations."""

    @staticmethod
    def find_by_id(label_id):
        """Find label by ID."""
        return Label.query.filter_by(id=label_id).first()

    @staticmethod
    def find_by_user_id(user_id):
        """Find all labels for a user."""
        return Label.query.filter_by(user_id=user_id).all()

    @staticmethod
    def create(user_id, name, **kwargs):
        """Create and save a new label."""
        label = Label(user_id=user_id, name=name, **kwargs)
        db.session.add(label)
        db.session.commit()
        return label

    @staticmethod
    def delete(label_id):
        """Delete a label."""
        label = Label.query.filter_by(id=label_id).first()
        if label:
            db.session.delete(label)
            db.session.commit()
            return True
        return False

    @staticmethod
    def count_by_user(user_id):
        """Count labels for a user."""
        return Label.query.filter_by(user_id=user_id).count()