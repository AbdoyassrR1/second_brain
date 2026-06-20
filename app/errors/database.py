#!/usr/bin/python3
"""Database error handlers."""

from flask import current_app, g, request
from sqlalchemy.exc import (
    DataError,
    DatabaseError,
    IntegrityError,
    OperationalError,
    ProgrammingError,
    SQLAlchemyError,
)

from app.shared.metrics import database_errors_total

from .base import _error_response


def _record_database_error(error, operation, message, error_code, status_code):
    """Log and count a database error before returning a response."""
    database_errors_total.labels(
        operation=operation,
        error_type=type(error).__name__,
    ).inc()

    current_app.logger.exception(
        "Database error",
        extra={
            "request_id": g.get("request_id"),
            "user_id": g.get("user_id"),
            "method": request.method,
            "path": request.path,
            "remote_addr": request.remote_addr,
            "operation": operation,
            "exception_type": type(error).__name__,
        },
    )

    return _error_response(message, error_code, status_code)


def register_database_error_handlers(app):
    """Register handlers for database and SQLAlchemy errors."""

    @app.errorhandler(IntegrityError)
    def integrity_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Database constraint violation.",
            error_code="CONFLICT",
            status_code=409,
        )

    @app.errorhandler(OperationalError)
    def operational_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Database service unavailable. Please try again later.",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503,
        )

    @app.errorhandler(DataError)
    def data_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Invalid data supplied for database operation.",
            error_code="INVALID_DATA",
            status_code=400,
        )

    @app.errorhandler(ProgrammingError)
    def programming_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Database query error.",
            error_code="DATABASE_ERROR",
            status_code=500,
        )

    @app.errorhandler(DatabaseError)
    def database_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Database error.",
            error_code="DATABASE_ERROR",
            status_code=500,
        )

    @app.errorhandler(SQLAlchemyError)
    def sqlalchemy_error(error):
        return _record_database_error(
            error,
            operation=request.endpoint or request.method or "database",
            message="Database error.",
            error_code="DATABASE_ERROR",
            status_code=500,
        )