#!/usr/bin/python3
"""Tasks feature models."""

from sqlalchemy import Column, String, Text, Date, Enum, ForeignKey, DateTime, Boolean, Table
from sqlalchemy.orm import relationship, backref
from app.shared.models import BaseModel
from app.extensions import db


# Many-to-many association table for tasks and labels
task_labels = Table(
    "task_labels",
    db.Model.metadata,
    Column("task_id", String(50), ForeignKey("tasks.id"), primary_key=True),
    Column("label_id", String(50), ForeignKey("labels.id"), primary_key=True),
)


class Task(BaseModel):
    """Task model for user task management."""

    __tablename__ = "tasks"

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum("todo", "in_progress", "completed", "cancelled", name="task_status"),
        default="todo",
        nullable=False,
    )
    priority = Column(
        Enum("low", "medium", "high", "urgent", name="task_priority"),
        default="medium",
        nullable=False,
    )
    due_date = Column(Date, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Archive / Soft delete columns
    is_archived = Column(Boolean, default=False, nullable=False)
    archived_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=True)
    parent_task_id = Column(String(50), ForeignKey("tasks.id"), nullable=True)

    # Relationships
    user = relationship("User", backref="tasks")
    project = relationship("Project", back_populates="tasks", foreign_keys=[project_id])
    subtasks = relationship(
        "Task",
        backref=backref("parent", remote_side="Task.id"),
        cascade="all, delete-orphan",
        foreign_keys=[parent_task_id],
    )
    labels = relationship("Label", secondary=task_labels, back_populates="tasks")

    def __repr__(self):
        return f"<Task: {self.title} ({self.status})>"