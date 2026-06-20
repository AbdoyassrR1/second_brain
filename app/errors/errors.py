#!/usr/bin/python3
"""Application-wide Flask error handlers."""

from flask import current_app, g, request
from .database import register_database_error_handlers
from .http import register_http_error_handlers
from .jwt import register_jwt_error_handlers
from .base import _error_response


def register_error_handlers(app):
    """Register all application error handlers."""

    register_database_error_handlers(app)
    register_http_error_handlers(app)
    register_jwt_error_handlers(app)

    @app.errorhandler(Exception)
    def unhandled_exception(error):
        request_id = g.get("request_id", "unknown")
        user_id = g.get("user_id", None)

        current_app.logger.exception(
            "Unhandled application exception",
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
            }
        )

        return _error_response(
            "Internal server error",
            "INTERNAL_ERROR",
            500
        )