#!/usr/bin/python3
"""Tests for redaction utilities."""

import pytest
from app.shared.middleware.redaction import sanitize_headers, redact_json_payload, sanitize_querystring


class TestSanitizeHeaders:
    """Test header sanitization."""

    def test_redacts_authorization(self):
        """Test that authorization header is redacted."""
        headers = {"Authorization": "Bearer my-secret-token", "User-Agent": "Mozilla"}
        result = sanitize_headers(headers)
        assert result["Authorization"] == "***"
        assert result["User-Agent"] == "Mozilla"

    def test_redacts_cookie(self):
        """Test that cookie header is redacted."""
        headers = {"Cookie": "session=abc123"}
        result = sanitize_headers(headers)
        assert result["Cookie"] == "***"

    def test_redacts_set_cookie(self):
        """Test that set-cookie header is redacted."""
        headers = {"Set-Cookie": "token=xyz"}
        result = sanitize_headers(headers)
        assert result["Set-Cookie"] == "***"

    def test_preserves_other_headers(self):
        """Test that non-sensitive headers are preserved."""
        headers = {"Content-Type": "application/json", "Accept": "*/*"}
        result = sanitize_headers(headers)
        assert result["Content-Type"] == "application/json"
        assert result["Accept"] == "*/*"

    def test_case_insensitive_matching(self):
        """Test that sensitive header matching is case-insensitive."""
        headers = {"AUTHORIZATION": "Bearer token"}
        result = sanitize_headers(headers)
        assert result["AUTHORIZATION"] == "***"


class TestRedactJsonPayload:
    """Test JSON payload redaction."""

    def test_redacts_password(self):
        """Test that password fields are redacted."""
        payload = {"username": "john", "password": "secret123"}
        result = redact_json_payload(payload)
        assert result["password"] == "***"
        assert result["username"] == "john"

    def test_redacts_token(self):
        """Test that token fields are redacted."""
        payload = {"token": "abc123"}
        result = redact_json_payload(payload)
        assert result["token"] == "***"

    def test_redacts_nested(self):
        """Test that nested sensitive fields are redacted."""
        payload = {"user": {"password": "secret", "name": "John"}, "api_key": "sk-123"}
        result = redact_json_payload(payload)
        assert result["user"]["password"] == "***"
        assert result["user"]["name"] == "John"
        assert result["api_key"] == "***"

    def test_handles_list(self):
        """Test redaction within lists."""
        payload = [{"password": "secret1"}, {"password": "secret2"}]
        result = redact_json_payload(payload)
        assert result[0]["password"] == "***"
        assert result[1]["password"] == "***"

    def test_preserves_non_sensitive(self):
        """Test that non-sensitive payloads are unchanged."""
        payload = {"name": "John", "age": 30}
        result = redact_json_payload(payload)
        assert result == payload


class TestSanitizeQuerystring:
    """Test query string sanitization."""

    def test_redacts_password_param(self):
        """Test that password parameter is redacted."""
        qs = sanitize_querystring("user=john&password=secret123")
        assert "secret123" not in qs
        assert "password=***" in qs

    def test_redacts_token_param(self):
        """Test that token parameter is redacted."""
        qs = sanitize_querystring("token=abc123")
        assert "token=***" in qs

    def test_redacts_api_key_param(self):
        """Test that api_key parameter is redacted."""
        qs = sanitize_querystring("api_key=sk-12345")
        assert "api_key=***" in qs

    def test_redacts_auth_param(self):
        """Test that auth parameter is redacted."""
        qs = sanitize_querystring("auth=basic&user=john")
        assert "auth=***" in qs

    def test_preserves_other_params(self):
        """Test that non-sensitive parameters are preserved."""
        qs = sanitize_querystring("name=test&page=1&sort=asc")
        assert qs == "name=test&page=1&sort=asc"

    def test_empty_string(self):
        """Test empty query string."""
        assert sanitize_querystring("") == ""
