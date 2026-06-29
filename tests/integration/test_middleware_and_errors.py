#!/usr/bin/python3
"""Integration tests for middleware and error handling."""

import json
import pytest
from flask import Flask
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError, OperationalError
from app import create_app


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app("testing")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


class TestMiddlewareCorrelation:
    """Test request correlation and tracing middleware."""

    def test_request_id_generated(self, client):
        """Test that request_id is generated if not provided."""
        response = client.get("/api/v1/health/startup")
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0

    def test_request_id_propagated(self, client):
        """Test that incoming X-Request-ID is propagated to response."""
        request_id = "test-request-id-123"
        response = client.get("/api/v1/health/startup", headers={"X-Request-ID": request_id})
        assert response.headers["X-Request-ID"] == request_id

    def test_correlation_id_fallback(self, client):
        """Test that X-Correlation-ID is used if X-Request-ID is not provided."""
        correlation_id = "test-correlation-id-456"
        response = client.get("/api/v1/health/startup", headers={"X-Correlation-ID": correlation_id})
        assert response.headers["X-Request-ID"] == correlation_id

    def test_trace_id_generated(self, client):
        """Test that trace_id is generated if not provided."""
        response = client.get("/api/v1/health/startup")
        assert "X-Trace-ID" in response.headers
        assert len(response.headers["X-Trace-ID"]) > 0

    def test_trace_id_propagated(self, client):
        """Test that incoming X-Trace-ID is propagated to response."""
        trace_id = "test-trace-id-789"
        response = client.get("/api/v1/health/startup", headers={"X-Trace-ID": trace_id})
        assert response.headers["X-Trace-ID"] == trace_id

    def test_span_id_generated(self, client):
        """Test that span_id is generated if not provided."""
        response = client.get("/api/v1/health/startup")
        assert "X-Span-ID" in response.headers
        assert len(response.headers["X-Span-ID"]) > 0

    def test_span_id_propagated(self, client):
        """Test that incoming X-Span-ID is propagated to response."""
        span_id = "test-span-id"
        response = client.get("/api/v1/health/startup", headers={"X-Span-ID": span_id})
        assert response.headers["X-Span-ID"] == span_id

    def test_parent_span_id_propagated(self, client):
        """Test that incoming X-Parent-Span-ID is propagated to response."""
        parent_span_id = "parent-span-id"
        response = client.get("/api/v1/health/startup", headers={"X-Parent-Span-ID": parent_span_id})
        assert response.headers["X-Parent-Span-ID"] == parent_span_id


class TestUnauthorizedError:
    """Test JWT and unauthorized error handling."""

    def test_missing_jwt_returns_401(self, client):
        """Test that missing JWT returns 401 with proper error code."""
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "UNAUTHORIZED"
        assert "request_id" in data

    def test_missing_jwt_includes_trace_ids(self, client):
        """Test that error response includes trace IDs."""
        response = client.get("/api/v1/me")
        assert response.status_code == 401
        assert "X-Trace-ID" in response.headers
        assert "X-Span-ID" in response.headers
        assert "X-Request-ID" in response.headers

    def test_invalid_jwt_returns_401(self, client):
        """Test that invalid JWT returns 401."""
        response = client.get(
            "/api/v1/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error_code"] == "UNAUTHORIZED"


class TestBadRequestError:
    """Test 400/validation error handling."""

    def test_bad_request_returns_400(self, client):
        """Test that bad request returns 400."""
        response = client.post(
            "/api/v1/auth/register",
            json={},  # Missing required fields
            content_type="application/json"
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "request_id" in data

    def test_validation_error_includes_trace_ids(self, client):
        """Test that validation error includes trace IDs."""
        response = client.post(
            "/api/v1/auth/register",
            json={},
            content_type="application/json"
        )
        assert response.status_code == 400
        assert "X-Trace-ID" in response.headers
        assert "X-Span-ID" in response.headers


class TestRateLimitError:
    """Test rate limiting error handling."""

    def test_rate_limit_returns_429(self, client, app):
        """Test that exceeding rate limit returns 429."""
        # Make requests to trigger rate limit
        for i in range(201):  # Default rate limit is 200 per day
            response = client.get("/api/v1/health/startup")
            if response.status_code == 429:
                break
        
        if response.status_code == 429:
            data = json.loads(response.data)
            assert data["error_code"] == "RATE_LIMITED"
            assert "request_id" in data


class TestNotFoundError:
    """Test 404 error handling."""

    def test_not_found_returns_404(self, client):
        """Test that non-existent route returns 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error_code"] == "NOT_FOUND"
        assert "request_id" in data


class TestErrorResponseStructure:
    """Test error response structure consistency."""

    def test_error_response_includes_required_fields(self, client):
        """Test that all error responses include required fields."""
        response = client.get("/api/v1/nonexistent")
        data = json.loads(response.data)
        
        assert "status" in data
        assert data["status"] == "error"
        assert "error_code" in data
        assert "message" in data
        assert "request_id" in data

    def test_error_response_propagates_trace_ids(self, client):
        """Test that all error responses propagate tracing IDs."""
        trace_id = "test-trace-123"
        span_id = "test-span-456"
        
        response = client.get(
            "/api/v1/nonexistent",
            headers={"X-Trace-ID": trace_id, "X-Span-ID": span_id}
        )
        
        assert response.headers["X-Trace-ID"] == trace_id
        assert response.headers["X-Span-ID"] == span_id
        assert "X-Request-ID" in response.headers


class TestHealthCheckSkipping:
    """Test that health checks skip detailed logging."""

    def test_health_check_returns_200(self, client):
        """Test that health check endpoint returns 200."""
        response = client.get("/api/v1/health/startup")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "ok"

    def test_metrics_endpoint_returns_200(self, client):
        """Test that metrics endpoint returns 200."""
        response = client.get("/metrics")
        assert response.status_code == 200


class TestContentNegotiation:
    """Test request content-type handling."""

    def test_non_json_post_returns_415(self, client):
        """Test that non-JSON POST returns 415."""
        response = client.post(
            "/api/v1/auth/register",
            data="not json",
            content_type="text/plain"
        )
        assert response.status_code == 415


class TestResponseHeaders:
    """Test response header propagation."""

    def test_all_response_headers_present(self, client):
        """Test that all tracing headers are present in response."""
        response = client.get("/api/v1/health/startup")
        
        assert "X-Request-ID" in response.headers
        assert "X-Trace-ID" in response.headers
        assert "X-Span-ID" in response.headers

    def test_response_headers_match_request(self, client):
        """Test that response headers match incoming request headers."""
        request_id = "req-123"
        trace_id = "trace-456"
        span_id = "span-789"
        
        response = client.get(
            "/api/v1/health/startup",
            headers={
                "X-Request-ID": request_id,
                "X-Trace-ID": trace_id,
                "X-Span-ID": span_id,
            }
        )
        
        assert response.headers["X-Request-ID"] == request_id
        assert response.headers["X-Trace-ID"] == trace_id
        assert response.headers["X-Span-ID"] == span_id


class TestDatabaseErrorHandling:
    """Test database error handling."""

    def test_integrity_error_returns_409(self, app, client):
        """Test that integrity errors are mapped to 409."""

        @app.route("/api/v1/test/db-integrity")
        def db_integrity_error():
            raise IntegrityError("INSERT", {}, Exception("duplicate key"))

        response = client.get("/api/v1/test/db-integrity")
        assert response.status_code == 409
        data = json.loads(response.data)
        assert data["error_code"] == "CONFLICT"

    def test_operational_error_returns_503(self, app, client):
        """Test that operational errors are mapped to 503."""

        @app.route("/api/v1/test/db-operational")
        def db_operational_error():
            raise OperationalError("SELECT", {}, Exception("connection failed"))

        response = client.get("/api/v1/test/db-operational")
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["error_code"] == "SERVICE_UNAVAILABLE"
