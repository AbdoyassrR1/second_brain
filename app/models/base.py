from uuid import uuid4
from app.app import db
from datetime import datetime
from sqlalchemy import Column, String,  DateTime



class BaseModel(db.Model):
    __abstract__ = True  # This makes the class abstract and not directly mapped to a table

    id = Column(String(50), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
