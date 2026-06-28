#!/usr/bin/python3
"""Decorators for routes and services."""

from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from .exceptions import UnauthorizedError, ForbiddenError


def auth_required(fn):
    """Decorator to require JWT authentication."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        if not user_id:
            raise UnauthorizedError()
        return fn(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """Decorator to check user role."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            # TODO: Load user and check role
            if "role" not in claims or claims["role"] not in allowed_roles:
                raise ForbiddenError("Access forbidden: insufficient role")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def require_json_body(payload_key="json_data", require_object=True):
    """Validate JSON request body and inject parsed payload into route kwargs."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Content-Type must be application/json",
                        }
                    ),
                    415,
                )

            payload = request.get_json(silent=True)
            if payload is None:
                return jsonify({"status": "error", "message": "Malformed JSON payload"}), 400

            if require_object and not isinstance(payload, dict):
                return jsonify({"status": "error", "message": "JSON payload must be an object"}), 400

            kwargs[payload_key] = payload
            return fn(*args, **kwargs)

        return wrapper

    return decorator
