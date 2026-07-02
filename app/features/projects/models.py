#!/usr/bin/python3
"""Projects feature models."""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.shared.models import BaseModel
from app.extensions import db


class Project(BaseModel):
    """Project model for grouping tasks."""

    __tablename__ = "projects"

    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    color = Column(String(7), nullable=True)  # hex color e.g. #FF5733

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", backref="projects")
    tasks = relationship("Task", back_populates="project", foreign_keys="Task.project_id")

    def __repr__(self):
        return f"<Project: {self.name}>"