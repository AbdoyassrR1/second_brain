#!/usr/bin/python3
"""Features module."""

from app.features.auth import auth_bp, me_bp
from app.features.tasks import tasks_bp
from app.features.reminders import reminders_bp
from app.features.health import health_bp
from app.features.projects import projects_bp
from app.features.labels import labels_bp

__all__ = ["auth_bp", "me_bp", "tasks_bp", "reminders_bp", "health_bp", "projects_bp", "labels_bp"]
