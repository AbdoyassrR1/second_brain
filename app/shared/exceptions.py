#!/usr/bin/python3
"""Custom exceptions for the application."""


class AppError(Exception):
    """Base application error."""

    def __init__(self, message, status_code=400, error_code="APP_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, message):
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR")


class NotFoundError(AppError):
    """Raised when a resource is not found."""

    def __init__(self, message):
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class UnauthorizedError(AppError):
    """Raised when user is not authenticated."""

    def __init__(self, message="Unauthorized"):
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class ForbiddenError(AppError):
    """Raised when user lacks permission."""

    def __init__(self, message="Forbidden"):
        super().__init__(message, status_code=403, error_code="FORBIDDEN")


class ConflictError(AppError):
    """Raised when resource conflicts (e.g., duplicate username)."""

    def __init__(self, message):
        super().__init__(message, status_code=409, error_code="CONFLICT")
