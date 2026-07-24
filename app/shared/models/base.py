#!/usr/bin/python3
"""Base model with common fields for all domain models."""

from uuid import uuid4
from app.extensions import db
from datetime import datetime, UTC
from sqlalchemy import Column, String, DateTime


class BaseModel(db.Model):
    """Abstract base model with id, created_at, updated_at fields."""

    __abstract__ = True

    id = Column(String(50), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
