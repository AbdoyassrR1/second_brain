#!/usr/bin/python3
import enum
from sqlalchemy import Column, String, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TransactionType(enum.Enum):
    INCOME = "Income"
    EXPENSE = "Expense"
    INVEST = "Invest"


class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(30), nullable=False)
    description = Column(Text)
    amount = Column(String(20), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)

    user = relationship("User", backref="transactions")

    def __repr__(self):
        return f"title: {self.title}, amount: {self.amount}, type: {self.type.value}"
    
    def to_dict(self):
        """Convert instance to dictionary"""
        TIME = "%a, %d %b %Y %I:%M:%S %p"
        return {
            "user_id": self.user_id,
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "amount": self.amount,
            "type": self.type.value,
            "created_at": self.created_at.strftime(TIME),
            "updated_at": self.updated_at.strftime(TIME)
        }
