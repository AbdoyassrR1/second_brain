#!/usr/bin/python3
"""Tests for custom exceptions."""

import pytest
from app.shared.exceptions import (
    AppError, ValidationError, NotFoundError,
    UnauthorizedError, ForbiddenError, ConflictError,
)


class TestAppError:
    """Test base AppError."""

    def test_base_app_error(self):
        """Test creating a base app error."""
        error = AppError("Something went wrong", 400)
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.status_code == 400

    def test_base_app_error_default_status(self):
        """Test base app error defaults to 400."""
        error = AppError("Default status")
        assert error.status_code == 400


class TestValidationError:
    """Test ValidationError."""

    def test_validation_error(self):
        """Test creating a validation error."""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.status_code == 400

    def test_validation_error_is_app_error(self):
        """Test ValidationError is an AppError."""
        error = ValidationError("test")
        assert isinstance(error, AppError)


class TestNotFoundError:
    """Test NotFoundError."""

    def test_not_found_error(self):
        """Test creating a not found error."""
        error = NotFoundError("User not found")
        assert error.message == "User not found"
        assert error.status_code == 404

    def test_not_found_error_is_app_error(self):
        """Test NotFoundError is an AppError."""
        error = NotFoundError("test")
        assert isinstance(error, AppError)


class TestUnauthorizedError:
    """Test UnauthorizedError."""

    def test_unauthorized_error(self):
        """Test creating an unauthorized error."""
        error = UnauthorizedError()
        assert error.message == "Unauthorized"
        assert error.status_code == 401

    def test_unauthorized_error_custom_message(self):
        """Test unauthorized error with custom message."""
        error = UnauthorizedError("Custom unauthorized message")
        assert error.message == "Custom unauthorized message"


class TestForbiddenError:
    """Test ForbiddenError."""

    def test_forbidden_error(self):
        """Test creating a forbidden error."""
        error = ForbiddenError()
        assert error.message == "Forbidden"
        assert error.status_code == 403

    def test_forbidden_error_custom_message(self):
        """Test forbidden error with custom message."""
        error = ForbiddenError("Access denied")
        assert error.message == "Access denied"


class TestConflictError:
    """Test ConflictError."""

    def test_conflict_error(self):
        """Test creating a conflict error."""
        error = ConflictError("Duplicate entry")
        assert error.message == "Duplicate entry"
        assert error.status_code == 409

    def test_conflict_error_is_app_error(self):
        """Test ConflictError is an AppError."""
        error = ConflictError("test")
        assert isinstance(error, AppError)
