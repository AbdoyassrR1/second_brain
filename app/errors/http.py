#!/usr/bin/python3
from flask import current_app, g, request
from marshmallow import ValidationError as MarshmallowValidationError
from .base import _error_response


def register_http_error_handlers(app):
    """Register shared HTTP and validation error handlers."""

    @app.errorhandler(400)
    def bad_request_error(error):
        return _error_response(
            str(error.description) or "Bad Request",
            "BAD_REQUEST",
            400
        )

    @app.errorhandler(MarshmallowValidationError)
    def marshmallow_validation_error(error):
        return _error_response(
            error.messages,
            "VALIDATION_ERROR",
            400
        )

    

    @app.errorhandler(401)
    def unauthorized_error(error):
        current_app.logger.warning(
            "Unauthorized access attempt",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
            }
        )
        return _error_response(
            str(error.description) or "Unauthorized",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(403)
    def forbidden_error(error):
        current_app.logger.warning(
            "Forbidden access attempt",
            extra={
                "request_id": g.get("request_id"),
                "user_id": g.get("user_id"),
                "path": request.path,
            }
        )
        return _error_response(
            str(error.description) or "Forbidden",
            "FORBIDDEN",
            403
        )

    @app.errorhandler(404)
    def not_found_error(error):
        return _error_response(
            str(error.description) or "Not Found",
            "NOT_FOUND",
            404
        )
    
    @app.errorhandler(405)
    def method_not_allowed_error(error):
        return _error_response(
            str(error.description) or "Method Not Allowed",
            "METHOD_NOT_ALLOWED",
            405
        )

    @app.errorhandler(409)
    def conflict_error(error):
        return _error_response(
            str(error.description) or "Conflict",
            "CONFLICT",
            409
        )

    @app.errorhandler(429)
    def ratelimit_error(error):
        from app.shared.metrics import rate_limit_exceeded_total
        # Avoid labeling by raw client IP to prevent high-cardinality series.
        rate_limit_exceeded_total.inc()
        
        current_app.logger.warning(
            "Rate limit exceeded",
            extra={
                "request_id": g.get("request_id"),
                "client_ip": request.remote_addr,
            }
        )
        return _error_response(
            "You have exceeded the maximum number of requests. Please try again later.",
            "RATE_LIMITED",
            429
        )

    @app.errorhandler(500)
    def internal_server_error(error):
        current_app.logger.error(
            "Internal server error",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
            }
        )
        return _error_response(
            "Internal server error",
            "INTERNAL_ERROR",
            500
        )

    @app.errorhandler(503)
    def service_unavailable_error(error):
        return _error_response(
            "Service temporarily unavailable",
            "SERVICE_UNAVAILABLE",
            503
        )
