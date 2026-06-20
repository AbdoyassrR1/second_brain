#!/usr/bin/python3
"""Unit tests for middleware and logging components."""

import json
import logging
import pytest
from io import StringIO
from app.shared.logging.logging_config import JSONFormatter, RequestContextFilter
from flask import Flask, g


class TestJSONFormatter:
    """Test structured JSON logging formatter."""

    def test_json_formatter_basic_output(self):
        """Test that JSONFormatter outputs valid JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"
        assert parsed["message"] == "Test message"
        assert parsed["line"] == 42

    def test_json_formatter_includes_extra_fields(self):
        """Test that JSONFormatter includes custom extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.request_id = "req-123"
        record.user_id = 456
        record.custom_field = "custom_value"
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert parsed["request_id"] == "req-123"
        assert parsed["user_id"] == 456
        assert parsed["custom_field"] == "custom_value"

    def test_json_formatter_handles_elapsed_alias(self):
        """Test that JSONFormatter aliases elapsed → elapsed_seconds."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        record.elapsed = 0.5
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        assert "elapsed_seconds" in parsed
        assert parsed["elapsed_seconds"] == 0.5
        assert "elapsed" not in parsed

    def test_json_formatter_excludes_standard_fields(self):
        """Test that JSONFormatter excludes standard LogRecord fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        output = formatter.format(record)
        parsed = json.loads(output)
        
        # Standard fields should not appear
        assert "msg" not in parsed
        assert "args" not in parsed
        assert "created" not in parsed


class TestRequestContextFilter:
    """Test request context filter."""

    def test_filter_adds_default_values_outside_context(self):
        """Test that filter adds default values outside request context."""
        filter_obj = RequestContextFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        result = filter_obj.filter(record)
        
        assert result is True
        assert record.request_id == "unknown"
        assert record.user_id is None
        assert record.trace_id == "unknown"
        assert record.span_id == "unknown"
        assert record.parent_span_id is None

    def test_filter_extracts_context_from_flask_g(self):
        """Test that filter extracts values from Flask g."""
        app = Flask(__name__)
        
        with app.app_context():
            g.request_id = "req-123"
            g.user_id = 789
            g.trace_id = "trace-456"
            g.span_id = "span-789"
            g.parent_span_id = "parent-span"
            
            filter_obj = RequestContextFilter()
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test",
                args=(),
                exc_info=None
            )
            
            result = filter_obj.filter(record)
            
            assert result is True
            assert record.request_id == "req-123"
            assert record.user_id == 789
            assert record.trace_id == "trace-456"
            assert record.span_id == "span-789"
            assert record.parent_span_id == "parent-span"


class TestSanitization:
    """Test query string sanitization."""

    def test_password_sanitization(self):
        """Test that password parameters are sanitized."""
        from app.shared.middleware.middleware import _sanitize_querystring
        
        qs = "user=john&password=secret123&action=login"
        sanitized = _sanitize_querystring(qs)
        
        assert "secret123" not in sanitized
        assert "password=***" in sanitized
        assert "user=john" in sanitized

    def test_api_key_sanitization(self):
        """Test that api_key parameters are sanitized."""
        from app.shared.middleware.middleware import _sanitize_querystring
        
        qs = "api_key=sk-12345&query=test"
        sanitized = _sanitize_querystring(qs)
        
        assert "sk-12345" not in sanitized
        assert "api_key=***" in sanitized
        assert "query=test" in sanitized

    def test_token_sanitization(self):
        """Test that token parameters are sanitized."""
        from app.shared.middleware.middleware import _sanitize_querystring
        
        qs = "token=abc123def456&operation=get"
        sanitized = _sanitize_querystring(qs)
        
        assert "abc123def456" not in sanitized
        assert "token=***" in sanitized


class TestErrorTypeClassification:
    """Test HTTP error type classification."""

    def test_classify_client_error(self):
        """Test classification of 4xx errors."""
        from app.shared.middleware.middleware import _get_error_type
        
        assert _get_error_type(400) == "client_error"
        assert _get_error_type(401) == "client_error"
        assert _get_error_type(403) == "client_error"
        assert _get_error_type(404) == "client_error"
        assert _get_error_type(499) == "client_error"

    def test_classify_server_error(self):
        """Test classification of 5xx errors."""
        from app.shared.middleware.middleware import _get_error_type
        
        assert _get_error_type(500) == "server_error"
        assert _get_error_type(502) == "server_error"
        assert _get_error_type(503) == "server_error"
        assert _get_error_type(599) == "server_error"

    def test_classify_unknown_error(self):
        """Test classification of other errors."""
        from app.shared.middleware.middleware import _get_error_type
        
        assert _get_error_type(200) == "unknown"
        assert _get_error_type(300) == "unknown"
