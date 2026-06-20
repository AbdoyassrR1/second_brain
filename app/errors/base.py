#!/usr/bin/python3
"""Shared error response helpers."""

from flask import jsonify, g


def _error_response(message, error_code, status_code):
    """Create a structured error response."""
    return jsonify({
        "status": "error",
        "error_code": error_code,
        "message": message if isinstance(message, str) else message,
        "request_id": g.get("request_id", "unknown"),
    }), status_code