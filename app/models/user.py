#!/usr/bin/python3
from app.models.base import BaseModel
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import relationship
import enum
from app.app import bcrypt


class UserRole(enum.Enum):
    USER = "User"
    ADMIN = "Admin"


class User(BaseModel, UserMixin):
    __tablename__ = 'users'

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(50), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER.value)

    # Relationships (if applicable)
    habits = relationship('Habit', backref='user')

    def __repr__(self):
        return f"<User {self.username}, Role: {self.role}>"

    # Set the password (hashed)
    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password)

    # Check if the password is correct
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    # Convert to dictionary for API response
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
