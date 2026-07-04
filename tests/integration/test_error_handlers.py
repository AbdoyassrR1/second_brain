#!/usr/bin/python3
"""Integration tests for error handlers."""
import json
import pytest
from flask import Flask
from sqlalchemy.exc import DataError, ProgrammingError, DatabaseError, SQLAlchemyError
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


class TestHTTPErrorHandlers:
    """Test HTTP error handlers."""

    def test_403_forbidden(self, app, client):
        """Test 403 error handler."""
        @app.route("/api/v1/test/403")
        def trigger_403():
            from flask import abort
            abort(403)

        response = client.get("/api/v1/test/403")
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data["error_code"] == "FORBIDDEN"
        assert "request_id" in data

    def test_405_method_not_allowed(self, app, client):
        """Test 405 error handler."""
        response = client.put("/api/v1/monitor/health")
        assert response.status_code == 405
        data = json.loads(response.data)
        assert data["error_code"] == "METHOD_NOT_ALLOWED"

    def test_500_internal_server_error(self, app, client):
        """Test 500 error handler."""
        @app.route("/api/v1/test/500")
        def trigger_500():
            raise RuntimeError("Unexpected error")

        response = client.get("/api/v1/test/500")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["error_code"] == "INTERNAL_ERROR"

    def test_503_service_unavailable(self, app, client):
        """Test 503 error handler."""
        @app.route("/api/v1/test/503")
        def trigger_503():
            from flask import abort
            abort(503)

        response = client.get("/api/v1/test/503")
        assert response.status_code == 503
        data = json.loads(response.data)
        assert data["error_code"] == "SERVICE_UNAVAILABLE"


class TestDatabaseErrorHandlers:
    """Test database error handlers."""

    def test_data_error_returns_400(self, app, client):
        """Test that DataError maps to 400."""
        @app.route("/api/v1/test/db-data-error")
        def db_data_error():
            raise DataError("INSERT", {}, Exception("invalid data"))

        response = client.get("/api/v1/test/db-data-error")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["error_code"] == "INVALID_DATA"

    def test_programming_error_returns_500(self, app, client):
        """Test that ProgrammingError maps to 500."""
        @app.route("/api/v1/test/db-programming")
        def db_programming_error():
            raise ProgrammingError("SELECT", {}, Exception("bad query"))

        response = client.get("/api/v1/test/db-programming")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["error_code"] == "DATABASE_ERROR"

    def test_database_error_returns_500(self, app, client):
        """Test that DatabaseError maps to 500."""
        @app.route("/api/v1/test/db-error")
        def db_database_error():
            raise DatabaseError("SELECT", {}, Exception("db error"))

        response = client.get("/api/v1/test/db-error")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["error_code"] == "DATABASE_ERROR"

    def test_sqlalchemy_error_returns_500(self, app, client):
        """Test that SQLAlchemyError maps to 500."""
        @app.route("/api/v1/test/db-sqlalchemy")
        def db_sqlalchemy_error():
            raise SQLAlchemyError("connection failed")

        response = client.get("/api/v1/test/db-sqlalchemy")
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["error_code"] == "DATABASE_ERROR"


class TestAppErrorHandlers:
    """Test custom application error handlers."""

    def test_validation_error(self, app, client):
        """Test ValidationError -> 400."""
        from app.shared.exceptions import ValidationError

        @app.route("/api/v1/test/validation-error")
        def trigger_validation_error():
            raise ValidationError("Invalid input provided")

        response = client.get("/api/v1/test/validation-error")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "VALIDATION" in data["error_code"]

    def test_not_found_error(self, app, client):
        """Test NotFoundError -> 404."""
        from app.shared.exceptions import NotFoundError

        @app.route("/api/v1/test/not-found")
        def trigger_not_found():
            raise NotFoundError("Resource not found")

        response = client.get("/api/v1/test/not-found")
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["error_code"] == "NOT_FOUND"

    def test_unauthorized_error(self, app, client):
        """Test UnauthorizedError -> 401."""
        from app.shared.exceptions import UnauthorizedError

        @app.route("/api/v1/test/unauthorized")
        def trigger_unauthorized():
            raise UnauthorizedError("Not authenticated")

        response = client.get("/api/v1/test/unauthorized")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert "UNAUTHORIZED" in data["error_code"]

    def test_forbidden_error(self, app, client):
        """Test ForbiddenError -> 403."""
        from app.shared.exceptions import ForbiddenError

        @app.route("/api/v1/test/forbidden")
        def trigger_forbidden():
            raise ForbiddenError("Access denied")

        response = client.get("/api/v1/test/forbidden")
        assert response.status_code == 403
        data = json.loads(response.data)
        assert "FORBIDDEN" in data["error_code"]

    def test_conflict_error(self, app, client):
        """Test ConflictError -> 409."""
        from app.shared.exceptions import ConflictError

        @app.route("/api/v1/test/conflict")
        def trigger_conflict():
            raise ConflictError("Duplicate entry")

        response = client.get("/api/v1/test/conflict")
        assert response.status_code == 409
        data = json.loads(response.data)
        assert "CONFLICT" in data["error_code"]




