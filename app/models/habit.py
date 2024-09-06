import enum
from sqlalchemy import Column, String, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class HabitStatus(enum.Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"



class Habit(BaseModel):
    __tablename__ = 'habits'

    title = Column(String(50), nullable=False)
    description = Column(Text)


    def __repr__(self) -> str:
        return f"Habit: {self.title}, id: {self.id}, created_at: {self.created_at}"

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
            }


class HabitEntry(BaseModel):
    __tablename__ = 'habit_entries'

    habit_id = Column(String(50), ForeignKey("habits.id"), nullable=False)
    notes = Column(Text)
    status = Column(Enum(HabitStatus), nullable=False)

    habit = relationship('Habit', backref='entries')

    def __repr__(self) -> str:
        return f"status: {self.status}, id: {self.id}, created_at: {self.created_at}"

    def to_dict(self):
        TIME = "%a, %d %b %Y %I:%M:%S %p"
        return {
            'id': self.id,
            "habit_id": self.habit_id,
            'status': self.status.value,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
            }
