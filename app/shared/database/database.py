#!/usr/bin/python3
"""Centralized transaction proxy for database writes.

All commits, rollbacks, adds, and deletes should go through the
``database`` singleton so that:

- commit()/rollback() error handling lives in exactly one place
- a failed commit always rolls the session back before re-raising
  (prevents the "zombie session" problem where the session is left
  in a broken state for the rest of the request)
- a single swap point exists if the underlying ORM/session API changes
- future cross-cutting concerns (retries, metrics, read/write routing)
  can attach here

Queries intentionally stay with the ORM (``Model.query``) in
repositories — that is the query seam, not this proxy.
"""

from flask import current_app

from app.extensions import db
from app.shared.metrics import database_errors_total


class Database:
    """Thin transaction proxy around the SQLAlchemy session."""

    @property
    def session(self):
        """Access to the raw session (honest escape hatch for special cases)."""
        return db.session

    def add(self, obj):
        db.session.add(obj)

    def delete(self, obj):
        db.session.delete(obj)

    def commit(self):
        try:
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            current_app.logger.error(
                "DB commit failed",
                extra={"exception_type": type(exc).__name__},
            )
            database_errors_total.labels(
                operation="commit", error_type=type(exc).__name__
            ).inc()
            raise

    def rollback(self):
        db.session.rollback()


database = Database()
