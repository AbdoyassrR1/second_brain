#!/usr/bin/python3
"""Shared error response helpers."""

from flask import jsonify, g


def _error_response(message, error_code, status_code, errors=None):
    """Create a structured error response."""
    response = {
        "status": "error",
        "error_code": error_code,
        "message": message if isinstance(message, str) else message,
        "request_id": g.get("request_id", "unknown"),
    }
    if errors is not None:
        response["errors"] = errors
    return jsonify(response), status_code