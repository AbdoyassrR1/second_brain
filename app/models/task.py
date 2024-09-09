#!/usr/bin/python3
import enum
from sqlalchemy import Column, String, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TaskStatus(enum.Enum):
    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    DONE = "Done"

class TaskPriority(enum.Enum):
    LOW = 'Low'
    MEDIUM = 'Medium'
    HIGH = 'High'

class TaskCategory(enum.Enum):
    WORK = 'Work'
    STUDY = 'Study'
    WORKOUT = 'Workout'


class Task(BaseModel):
    __tablename__ = 'tasks'

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(50), nullable=False, unique=True)
    description = Column(Text)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.TODO)
    priority = Column(Enum(TaskPriority), nullable=False)
    category = Column(Enum(TaskCategory), nullable=False)

    user = relationship('User', backref="tasks")

    def __repr__(self):
        return f"title: {self.title}, id: {self.id}, user_id: {self.user_id}"

    def to_dict(self):
        """Convert instance to dictionary"""
        TIME = "%a, %d %b %Y %I:%M:%S %p"
        return {
            'user_id': self.user_id,
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'category': self.category.value,
            'created_at': self.created_at.strftime(TIME),
            'updated_at': self.updated_at.strftime(TIME)
        }
