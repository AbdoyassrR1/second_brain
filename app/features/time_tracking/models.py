#!/usr/bin/python3
"""Time tracking feature models."""

from datetime import datetime, UTC

from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.extensions import db
from app.shared.models import BaseModel


class TimeEntry(BaseModel):
    """A logged time period.

    ``running=True`` (and ``ended_at``/``duration_seconds`` NULL) identifies an
    active timer. At most one running entry is allowed per user (service-enforced).
    """

    __tablename__ = "time_entries"

    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    running = Column(Boolean, nullable=False, default=False)
    note = Column(Text, nullable=True)

    task_links = relationship(
        "TimeEntryTask",
        back_populates="time_entry",
        cascade="all, delete-orphan",
        order_by="[TimeEntryTask.position.asc(), TimeEntryTask.created_at.asc(), TimeEntryTask.time_entry_id.asc()]",
    )

    __table_args__ = (
        Index("ix_time_entries_user_running", "user_id", "running"),
        Index("ix_time_entries_running_started", "running", "started_at"),
        Index("ix_time_entries_user_started", "user_id", "started_at"),
    )

    def __repr__(self):
        state = "running" if self.running else "completed"
        return f"<TimeEntry: {self.id} ({state}, {self.duration_seconds}s)>"


class TimeEntryTask(db.Model):
    """Junction linking a time entry to tasks, with per-task allocation."""

    __tablename__ = "time_entry_tasks"

    time_entry_id = Column(
        String(50), ForeignKey("time_entries.id", ondelete="CASCADE"), primary_key=True
    )
    task_id = Column(String(50), ForeignKey("tasks.id"), primary_key=True, index=True)
    allocated_seconds = Column(Integer, nullable=True)
    task_title = Column(String(200), nullable=True)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    time_entry = relationship("TimeEntry", back_populates="task_links")
    task = relationship("Task")

    @property
    def is_deleted(self):
        """Delegate to the linked task (reports surface deleted tasks explicitly)."""
        return bool(self.task is not None and self.task.is_deleted)

    @property
    def is_archived(self):
        """Delegate to the linked task."""
        return bool(self.task is not None and self.task.is_archived)

    def __repr__(self):
        return f"<TimeEntryTask: entry={self.time_entry_id} task={self.task_id} allocated={self.allocated_seconds}>"
