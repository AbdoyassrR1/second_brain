#!/usr/bin/python3
"""Reminders feature models."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from datetime import datetime, timedelta, UTC
from app.shared.models import BaseModel


class Reminder(BaseModel):
    """Reminder model for task reminders."""

    __tablename__ = "reminders"

    reminder_time = Column(DateTime(timezone=True), nullable=False)
    is_sent = Column(
        Enum(
            "pending",
            "sent",
            "failed",
            name="reminder_status",
        ),
        default="pending",
        nullable=False,
    )

    # ForeignKeys
    task_id = Column(String(50), ForeignKey("tasks.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Reminder: Task {self.task_id} at {self.reminder_time}>"

    def set_expiry(self, minutes=15):
        """Set reminder expiration time."""
        self.expiry_date = datetime.now(UTC) + timedelta(minutes=minutes)