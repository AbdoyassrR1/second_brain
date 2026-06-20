#!/usr/bin/python3
"""Middleware for request/response processing."""

import time
from uuid import uuid4
from flask import g, request, current_app
from app.shared.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_requests_errors_total,
)
from app.shared.middleware.redaction import sanitize_headers, redact_json_payload, sanitize_querystring

# Health check endpoints to skip logging
HEALTH_CHECK_PATHS = ["/api/v1/monitor/health", "/api/v1/monitor/ready", "/metrics"]


def setup_middleware(app):
    """Register middleware with Flask app."""

    @app.before_request
    def before_request():
        """Log incoming request and attach correlation/tracing IDs."""
        # Attach request context
        g.request_id = request.headers.get("X-Request-ID") or request.headers.get("X-Correlation-ID") or uuid4().hex
        
        # Distributed tracing: extract or generate trace/span IDs
        # Support W3C Trace Context (traceparent) and X-Trace-ID formats
        g.trace_id = _extract_trace_id(request.headers.get("X-Trace-ID"), request.headers.get("traceparent"))
        g.span_id = request.headers.get("X-Span-ID") or uuid4().hex[:16]  # Shorter span ID
        g.parent_span_id = request.headers.get("X-Parent-Span-ID")
        
        g.start_time = time.time()
        g.is_health_check = request.path in HEALTH_CHECK_PATHS

        # Skip detailed logging for health checks (too noisy)
        if g.is_health_check:
            return

        # Sanitize query string (remove sensitive parameters)
        safe_qs = sanitize_querystring(request.query_string.decode("utf-8") if request.query_string else "")
        # Sanitize headers for logging
        safe_headers = sanitize_headers({k: v for k, v in request.headers.items()})
        url = request.path
        if safe_qs:
            url += f"?{safe_qs}"

        current_app.logger.info(
            "Incoming request",
            extra={
                "request_id": g.request_id,
                "trace_id": g.trace_id,
                "span_id": g.span_id,
                "parent_span_id": g.parent_span_id,
                "method": request.method,
                "path": request.path,
                "endpoint": request.endpoint or "unknown",
                "url": url,
                "remote_addr": request.remote_addr,
                "user_agent": safe_headers.get("User-Agent"),
                "content_length": request.content_length,
            },
        )

    @app.after_request
    def after_request(response):
        """Log outgoing response and record metrics."""
        if hasattr(g, "start_time"):
            elapsed = time.time() - g.start_time
            # Prefer route template (url_rule.rule) to avoid high-cardinality from raw paths
            url_rule = getattr(request, "url_rule", None)
            route_label = url_rule.rule if url_rule else (request.endpoint or "unknown")
            status_code = response.status_code

            # Record metrics
            if not g.is_health_check:
                http_requests_total.labels(
                    method=request.method,
                    endpoint=route_label,
                    status_code=status_code,
                ).inc()

                http_request_duration_seconds.labels(
                    method=request.method,
                    endpoint=route_label,
                ).observe(elapsed)

                # Track errors
                if status_code >= 400:
                    error_type = _get_error_type(status_code)
                    http_requests_errors_total.labels(
                        method=request.method,
                        endpoint=route_label,
                        error_type=error_type,
                    ).inc()

            # Detailed logging (skip health checks)
            if not g.is_health_check:
                response_size = response.headers.get("Content-Length", "unknown")
                current_app.logger.info(
                    "Response sent",
                    extra={
                        "request_id": g.request_id,
                        "trace_id": g.trace_id,
                        "span_id": g.span_id,
                        "method": request.method,
                        "path": request.path,
                        "route": route_label,
                        "status_code": status_code,
                        "elapsed": elapsed,
                        "response_size": response_size,
                        "user_agent": request.headers.get("User-Agent"),
                        "content_length": request.content_length,
                    },
                )

            # Add tracing headers to response for client/downstream service
            response.headers["X-Request-ID"] = g.request_id
            response.headers["X-Trace-ID"] = g.trace_id
            response.headers["X-Span-ID"] = g.span_id
            if g.parent_span_id:
                response.headers["X-Parent-Span-ID"] = g.parent_span_id

        return response


def _sanitize_querystring(qs):
    """Remove sensitive parameters from query string."""
    if not qs:
        return ""
    # Deprecated local function; moved to app/shared/redaction.py
    return sanitize_querystring(qs)


def _extract_trace_id(explicit_trace_id, traceparent):
    """Extract a trace ID from headers or generate one.

    X-Trace-ID wins if present. Otherwise, use the trace ID from a W3C
    traceparent header when available. If neither exists, generate a UUID.
    """
    if explicit_trace_id:
        return explicit_trace_id

    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 2 and parts[1]:
            return parts[1]

    return uuid4().hex


def _get_error_type(status_code):
    """Categorize HTTP status code."""
    if 400 <= status_code < 500:
        return "client_error"
    elif 500 <= status_code < 600:
        return "server_error"
    else:
        return "unknown"
