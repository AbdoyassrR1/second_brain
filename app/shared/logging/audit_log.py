#!/usr/bin/python3
"""Audit logging for security and compliance events."""

import logging
from datetime import datetime, UTC
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
            "timestamp": datetime.now(UTC).isoformat(),
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

def log_2fa_enabled(user_id):
    """Log when 2FA is enabled for a user."""
    log_audit_event("2FA_ENABLED", user_id=user_id, success=True)


def log_2fa_disabled(user_id):
    """Log when 2FA is disabled for a user."""
    log_audit_event("2FA_DISABLED", user_id=user_id, success=True)


def log_otp_sent(user_id, email):
    """Log when an OTP is sent to a user's email."""
    log_audit_event("OTP_SENT", user_id=user_id, success=True, details={"email": email})


def log_otp_verified(user_id, email):
    """Log when an OTP is successfully verified."""
    log_audit_event("OTP_VERIFIED", user_id=user_id, success=True, details={"email": email})


def log_otp_failed(user_id, reason):
    """Log when OTP verification fails."""
    log_audit_event("OTP_FAILED", user_id=user_id, success=False, details={"reason": reason})


def log_project_create(user_id, project_id):
    """Log project creation."""
    log_audit_event(
        "PROJECT_CREATED",
        user_id=user_id,
        success=True,
        details={"project_id": project_id},
    )


def log_project_update(user_id, project_id, changes):
    """Log project update."""
    log_audit_event(
        "PROJECT_UPDATED",
        user_id=user_id,
        success=True,
        details={"project_id": project_id, "changed_fields": list(changes.keys())},
    )


def log_project_delete(user_id, project_id):
    """Log project deletion."""
    log_audit_event(
        "PROJECT_DELETED",
        user_id=user_id,
        success=True,
        details={"project_id": project_id},
    )


def log_label_create(user_id, label_id):
    """Log label creation."""
    log_audit_event(
        "LABEL_CREATED",
        user_id=user_id,
        success=True,
        details={"label_id": label_id},
    )


def log_label_delete(user_id, label_id):
    """Log label deletion."""
    log_audit_event(
        "LABEL_DELETED",
        user_id=user_id,
        success=True,
        details={"label_id": label_id},
    )


def log_label_assigned(user_id, task_id, label_id):
    """Log label assignment to task."""
    log_audit_event(
        "LABEL_ASSIGNED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id, "label_id": label_id},
    )


def log_label_removed(user_id, task_id, label_id):
    """Log label removal from task."""
    log_audit_event(
        "LABEL_REMOVED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id, "label_id": label_id},
    )


def log_task_archived(user_id, task_id):
    """Log task archiving."""
    log_audit_event(
        "TASK_ARCHIVED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_task_restored(user_id, task_id):
    """Log task restoration from archive."""
    log_audit_event(
        "TASK_RESTORED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_task_soft_deleted(user_id, task_id):
    """Log task soft deletion."""
    log_audit_event(
        "TASK_SOFT_DELETED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_task_recovered(user_id, task_id):
    """Log task recovery from soft delete."""
    log_audit_event(
        "TASK_RECOVERED",
        user_id=user_id,
        success=True,
        details={"task_id": task_id},
    )


def log_timer_started(user_id, entry_id, task_ids):
    """Log timer start."""
    log_audit_event(
        "TIMER_STARTED",
        user_id=user_id,
        success=True,
        details={"time_entry_id": entry_id, "task_ids": list(task_ids)},
    )


def log_timer_stopped(user_id, entry_id, duration_seconds, allocations=None):
    """Log timer stop."""
    log_audit_event(
        "TIMER_STOPPED",
        user_id=user_id,
        success=True,
        details={
            "time_entry_id": entry_id,
            "duration_seconds": duration_seconds,
            "allocations": allocations,
        },
    )


def log_timer_auto_stopped(user_id, entry_id, duration_seconds, reason):
    """Log timer auto-stop (long-running limit / account delete)."""
    log_audit_event(
        "TIMER_AUTO_STOPPED",
        user_id=user_id,
        success=True,
        details={
            "time_entry_id": entry_id,
            "duration_seconds": duration_seconds,
            "reason": reason,
        },
    )


def log_timer_task_added(user_id, entry_id, added, skipped):
    """Log tasks added to a running timer."""
    log_audit_event(
        "TIMER_TASK_ADDED",
        user_id=user_id,
        success=True,
        details={
            "time_entry_id": entry_id,
            "added": list(added),
            "skipped": list(skipped),
        },
    )


def log_timer_task_removed(user_id, entry_id, task_id):
    """Log task removed from a running timer."""
    log_audit_event(
        "TIMER_TASK_REMOVED",
        user_id=user_id,
        success=True,
        details={"time_entry_id": entry_id, "task_id": task_id},
    )


def log_time_entry_created(user_id, entry_id, task_ids, duration_seconds, source):
    """Log manual time entry creation."""
    log_audit_event(
        "TIME_ENTRY_CREATED",
        user_id=user_id,
        success=True,
        details={
            "time_entry_id": entry_id,
            "task_ids": list(task_ids),
            "duration_seconds": duration_seconds,
            "source": source,
        },
    )


def log_time_entry_updated(user_id, entry_id, changes):
    """Log time entry update."""
    log_audit_event(
        "TIME_ENTRY_UPDATED",
        user_id=user_id,
        success=True,
        details={"time_entry_id": entry_id, "changed_fields": list(changes)},
    )


def log_time_entry_deleted(user_id, entry_id):
    """Log time entry deletion."""
    log_audit_event(
        "TIME_ENTRY_DELETED",
        user_id=user_id,
        success=True,
        details={"time_entry_id": entry_id},
    )


def log_report_generated(user_id, group_by, from_dt, to_dt, tz):
    """Log report generation."""
    log_audit_event(
        "REPORT_GENERATED",
        user_id=user_id,
        success=True,
        details={
            "group_by": group_by,
            "from": from_dt.isoformat() if from_dt else None,
            "to": to_dt.isoformat() if to_dt else None,
            "tz": tz,
        },
    )


def log_time_entry_guard_blocked(user_id, task_ids, time_entry_id):
    """Log a tasks-feature mutation blocked by a running timer link."""
    log_audit_event(
        "TIME_ENTRY_GUARD_BLOCKED",
        user_id=user_id,
        success=False,
        details={"task_ids": list(task_ids), "time_entry_id": time_entry_id},
    )
