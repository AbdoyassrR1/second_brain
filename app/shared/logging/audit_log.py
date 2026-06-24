#!/usr/bin/python3
"""Audit logging for security and compliance events."""

import logging
from datetime import datetime, timezone
from flask import g, request

audit_logger = logging.getLogger("audit")


def log_audit_event(event_type, user_id=None, success=True, details=None):
    """
    Log an audit event for compliance and security.
    
    Args:
        event_type: Type of event (LOGIN, LOGOUT, REGISTER, DELETE_USER, etc.)
        user_id: ID of the user performing the action (or being acted upon)
        success: Whether the action succeeded
        details: Additional event-specific details
    """
    if details is None:
        details = {}

    audit_logger.info(
        f"Audit: {event_type}",
        extra={
            "request_id": g.get("request_id", "unknown"),
            "event_type": event_type,
            "user_id": user_id,
            "success": success,
            "remote_addr": request.remote_addr if request else None,
            "user_agent": request.headers.get("User-Agent") if request else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **details,
        },
    )


def log_login_attempt(email, success, reason=None):
    """Log login attempt."""
    details = {}
    if reason:
        details["reason"] = reason

    log_audit_event("LOGIN_ATTEMPT", user_id=email, success=success, details=details)


def log_registration(user_id, username, email):
    """Log user registration."""
    log_audit_event(
        "REGISTRATION",
        user_id=user_id,
        success=True,
        details={"username": username, "email": email},
    )


def log_logout(user_id):
    """Log user logout."""
    log_audit_event("LOGOUT", user_id=user_id, success=True)


def log_profile_update(user_id, changes):
    """Log profile update."""
    log_audit_event(
        "PROFILE_UPDATE",
        user_id=user_id,
        success=True,
        details={"changed_fields": list(changes.keys())},
    )


def log_task_create(user_id, task_id):
    """Log task creation."""
    log_audit_event(
        "TASK_CREATED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_task_delete(user_id, task_id):
    """Log task deletion."""
    log_audit_event(
        "TASK_DELETED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_task_complete(user_id, task_id):
    """Log task completion."""
    log_audit_event(
        "TASK_COMPLETED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_reminder_created(user_id, reminder_id, task_id):
    """Log reminder creation."""
    log_audit_event(
        "REMINDER_CREATED",
        user_id=user_id,
        success=True,
        details={"reminder_id": reminder_id, "task_id": task_id},
    )


def log_auth_failure(email, reason):
    """Log authentication failure."""
    log_audit_event("AUTH_FAILURE", user_id=email, success=False, details={"reason": reason})


def log_password_reset_requested(user_id, email):
    """Log password reset request."""
    log_audit_event("PASSWORD_RESET_REQUESTED", user_id=user_id, success=True, details={"email": email})


def log_password_reset_completed(user_id):
    """Log successful password reset."""
    log_audit_event("PASSWORD_RESET_COMPLETED", user_id=user_id, success=True)


def log_password_changed(user_id):
    """Log password change while logged in."""
    log_audit_event("PASSWORD_CHANGED", user_id=user_id, success=True)


def log_account_locked(user_id, locked_until):
    """Log account lockout after too many failed attempts."""
    log_audit_event(
        "ACCOUNT_LOCKED",
        user_id=user_id,
        success=False,
        details={"locked_until": locked_until.isoformat() if locked_until else None},
    )


def log_account_deleted(user_id):
    """Log account deletion."""
    log_audit_event("ACCOUNT_DELETED", user_id=user_id, success=True)


def log_device_login(user_id, device_name, ip_address):
    """Log device/session recorded at login."""
    log_audit_event(
        "DEVICE_LOGIN",
        user_id=user_id,
        success=True,
        details={"device_name": device_name, "ip_address": ip_address},
    )
