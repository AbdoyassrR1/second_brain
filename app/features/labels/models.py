#!/usr/bin/python3
"""Labels feature models."""

from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from app.shared.models import BaseModel
from app.extensions import db
from app.features.tasks.models import task_labels


class Label(BaseModel):
    """Label model for tagging tasks."""

    __tablename__ = "labels"

    name = Column(String(50), nullable=False)
    color = Column(String(7), nullable=True)  # hex color e.g. #FF5733

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Relationships
    user = relationship("User", backref="labels")
    tasks = relationship("Task", secondary=task_labels, back_populates="labels")

    def __repr__(self):
        return f"<Label: {self.name}>"