#!/usr/bin/python3
"""SQLAlchemy event listeners for database observability.

Registers query timing metrics and slow-query logging on the application's
engines. These events fire for every cursor execution regardless of how the
query was constructed (Model.query, session.scalars, bulk ops), so they
cover 100% of database traffic with no application-code changes.
"""

import time

from sqlalchemy import event
from flask import current_app

from app.shared.metrics import database_query_duration_seconds

SLOW_QUERY_THRESHOLD_SECONDS = 0.5


def _start_timer(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("_query_start_times", []).append(time.perf_counter())


def _record_duration(conn, cursor, statement, parameters, context, executemany):
    start_times = conn.info.get("_query_start_times", [])
    if not start_times:
        return
    start = start_times.pop()
    duration = time.perf_counter() - start

    # Derive the operation type from the leading keyword of the statement.
    operation = _statement_operation(statement)

    database_query_duration_seconds.labels(
        operation=operation, table=""
    ).observe(duration)

    if duration > SLOW_QUERY_THRESHOLD_SECONDS:
        current_app.logger.warning(
            "Slow query detected",
            extra={
                "duration_seconds": round(duration, 4),
                "operation": operation,
            },
        )


def _statement_operation(statement):
    """Return the SQL operation keyword (SELECT/INSERT/UPDATE/DELETE/...)."""
    if not statement:
        return "unknown"
    keyword = statement.lstrip().split(None, 1)[0]
    return keyword.upper() if keyword else "unknown"


def register_db_events(app):
    """Attach query timing listeners to every engine used by the app."""
    db = app.extensions.get("sqlalchemy")
    if db is None:
        return

    # db.engines resolves against current_app, so resolve them inside an
    # app context (create_app calls this before the app is returned).
    with app.app_context():
        engines = getattr(db, "engines", None) or {}

    for engine in engines.values():
        event.listen(engine, "before_cursor_execute", _start_timer)
        event.listen(engine, "after_cursor_execute", _record_duration)
