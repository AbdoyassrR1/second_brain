#!/usr/bin/python3
import enum
from sqlalchemy import Column, String, Enum, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class TransactionType(enum.Enum):
    INCOME = "Income"
    EXPENSE = "Expense"
    INVESTMENT = "Investment"


class TransactionSubCategory(enum.Enum):
    FOOD = "Food"
    TRANSPORTATION = "Transportation"
    HOUSING = "Housing"
    ENTERTAINMENT = "Entertainment"
    OTHER = "Other"



class Transaction(BaseModel):
    __tablename__ = "transactions"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(30), nullable=False)
    description = Column(Text)
    amount = Column(Float(), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    sub_category = Column(Enum(TransactionSubCategory), nullable=True)

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
            "sub_category": self.sub_category.value if self.sub_category else None,
            "created_at": self.created_at.strftime(TIME),
            "updated_at": self.updated_at.strftime(TIME)
        }
