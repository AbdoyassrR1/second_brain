#!/usr/bin/python3
"""Helpers to redact sensitive data from logs and metrics."""

from typing import Dict, Any

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie"}
SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "ssn", "card_number"}


def sanitize_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy of headers with sensitive values redacted."""
    out = {}
    for k, v in headers.items():
        if k.lower() in SENSITIVE_HEADERS:
            out[k] = "***"
        else:
            out[k] = v
    return out


def redact_json_payload(obj: Any) -> Any:
    """Recursively redact sensitive keys in JSON-like payloads.

    Leaves other values untouched. Returns a new structure.
    """
    if isinstance(obj, dict):
        new = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                new[k] = "***"
            else:
                new[k] = redact_json_payload(v)
        return new
    if isinstance(obj, list):
        return [redact_json_payload(i) for i in obj]
    return obj


def sanitize_querystring(qs: str) -> str:
    """Remove sensitive parameters from a query string.

    Input is the raw query string (without leading '?'), returns a sanitized
    query string where sensitive parameter values are replaced with '***'.
    """
    if not qs:
        return ""

    parts = qs.split("&")
    sanitized = []
    for part in parts:
        key, sep, value = part.partition("=")
        if any(s in key.lower() for s in SENSITIVE_KEYS | {"auth", "bearer", "key"}):
            sanitized.append(f"{key}=***")
        else:
            sanitized.append(part)

    return "&".join(sanitized)
