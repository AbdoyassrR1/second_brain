#!/usr/bin/python3
"""Structured logging configuration for the application."""

import logging
import json
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from flask import g, request
from flask import current_app


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON logs."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add service metadata when available
        try:
            log_data["service.name"] = current_app.config.get("SERVICE_NAME")
            log_data["service.version"] = current_app.config.get("SERVICE_VERSION")
            log_data["environment"] = current_app.config.get("ENVIRONMENT")
        except RuntimeError:
            # Not in app context
            pass

        # Capture all extra fields (any field not part of standard LogRecord)
        # Standard LogRecord fields to exclude
        standard_fields = {
            "name", "msg", "args", "created", "filename", "funcName", "levelname", "levelno",
            "lineno", "module", "msecs", "message", "pathname", "process", "processName",
            "relativeCreated", "thread", "threadName", "exc_info", "exc_text", "stack_info",
            "getMessage", "taskName"
        }
        
        # Add any extra fields that were passed in the extra dict
        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                # Handle elapsed → elapsed_seconds alias for consistency
                if key == "elapsed":
                    log_data["elapsed_seconds"] = value
                else:
                    log_data[key] = value

        # Add exception traceback if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class RequestContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record):
        """Inject request context into log record."""
        # Accessing `g` outside an active Flask request context raises
        # a RuntimeError. Guard access so logging emitted during startup
        # or background tasks does not crash.
        try:
            record.request_id = g.get("request_id", "unknown")
            # Preserve explicit user_id passed through logger extra.
            if not hasattr(record, "user_id") or record.user_id is None:
                record.user_id = g.get("user_id", None)
            record.trace_id = g.get("trace_id", "unknown")
            record.span_id = g.get("span_id", "unknown")
            record.parent_span_id = g.get("parent_span_id")
        except RuntimeError:
            record.request_id = "unknown"
            if not hasattr(record, "user_id"):
                record.user_id = None
            record.trace_id = "unknown"
            record.span_id = "unknown"
            record.parent_span_id = None

        # Add minimal service metadata as well (safe outside request context)
        try:
            record.service_name = current_app.config.get("SERVICE_NAME")
            record.service_version = current_app.config.get("SERVICE_VERSION")
            record.environment = current_app.config.get("ENVIRONMENT")
        except RuntimeError:
            record.service_name = None
            record.service_version = None
            record.environment = None
        return True


def setup_logging(app):
    """Configure application logging."""
    # Remove default handlers
    app.logger.handlers.clear()
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # Create formatters
    json_formatter = JSONFormatter()

    # Add request context filter
    request_filter = RequestContextFilter()

    if app.debug:
        # Development: log to console with JSON format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        console_handler.addFilter(request_filter)
        app.logger.addHandler(console_handler)
    else:
        # Production: log to file with rotation
        log_dir = os.getenv("LOG_DIR", "/var/log/app")
        os.makedirs(log_dir, exist_ok=True)

        # Application logs
        app_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=30,  # Keep 30 files = 300MB
        )
        app_handler.setFormatter(json_formatter)
        app_handler.addFilter(request_filter)
        app_handler.setLevel(logging.INFO)
        app.logger.addHandler(app_handler)

        # Error logs (separate file)
        error_handler = RotatingFileHandler(
            os.path.join(log_dir, "error.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=30,
        )
        error_handler.setFormatter(json_formatter)
        error_handler.addFilter(request_filter)
        error_handler.setLevel(logging.ERROR)
        app.logger.addHandler(error_handler)

    # Audit logger (always to file, separate from app logs)
    audit_logger = logging.getLogger("audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.handlers.clear()

    if not app.debug:
        audit_handler = RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=90,  # Keep 90 days of audit logs
        )
        audit_handler.setFormatter(json_formatter)
        audit_handler.addFilter(request_filter)
        audit_logger.addHandler(audit_handler)
    else:
        # Dev: still log audit events to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        console_handler.addFilter(request_filter)
        audit_logger.addHandler(console_handler)

    # Configure Werkzeug logger (Flask's access logs)
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.INFO)
    werkzeug_logger.handlers.clear()
    werkzeug_logger.propagate = False  # Prevent duplicate logs

    if app.debug:
        # Development: Werkzeug logs to console with JSON format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        console_handler.addFilter(request_filter)
        werkzeug_logger.addHandler(console_handler)
    else:
        # Production: Werkzeug logs to access.log with rotation
        access_handler = RotatingFileHandler(
            os.path.join(log_dir, "access.log"),
            maxBytes=10 * 1024 * 1024,
            backupCount=30,
        )
        access_handler.setFormatter(json_formatter)
        access_handler.addFilter(request_filter)
        werkzeug_logger.addHandler(access_handler)

    return audit_logger
