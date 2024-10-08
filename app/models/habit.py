import enum
from sqlalchemy import Column, String, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class HabitStatus(enum.Enum):
    ACTIVE = "Active"
    COMPLETED = "Completed"


class HabitEntryStatus(enum.Enum):
    COMPLETED = "Completed"
    SKIPPED = "Skipped"


class Habit(BaseModel):
    __tablename__ = "habits"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(40), nullable=False)
    status = Column(Enum(HabitStatus), nullable=False, default=HabitStatus.ACTIVE.value)
    description = Column(Text, nullable=False)

    user = relationship('User', backref="habits")

    def __repr__(self) -> str:
        return f"Habit: {self.title}, id: {self.id}, created_at: {self.created_at}"

    def to_dict(self):
        TIME = "%a, %d %b %Y %I:%M:%S %p"
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "status": self.status.value,
            "description": self.description,
            "created_at": self.created_at.strftime(TIME),
            "updated_at": self.updated_at.strftime(TIME)
            }


class HabitEntry(BaseModel):
    __tablename__ = "habit_entries"

    habit_id = Column(String(36), ForeignKey("habits.id"), nullable=False)
    notes = Column(Text)
    status = Column(Enum(HabitEntryStatus))

    habit = relationship("Habit", backref="entries")

    def __repr__(self) -> str:
        return f"status: {self.status}, id: {self.id}, created_at: {self.created_at}"

    def to_dict(self):
        TIME = "%a, %d %b %Y %I:%M:%S %p"
        return {
            "id": self.id,
            "habit_id": self.habit_id,
            "status": self.status.value if self.status else None,
            "notes": self.notes,
            "created_at": self.created_at.strftime(TIME),
            "updated_at": self.updated_at.strftime(TIME)
            }
