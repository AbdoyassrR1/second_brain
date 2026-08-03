#!/usr/bin/python3
"""Centralized database access layer.

Provides the transaction proxy singleton and observability wiring.
"""

from .database import database
from .events import register_db_events

__all__ = ["database", "register_db_events"]
