#!/usr/bin/python3
"""Prometheus metrics for observability (RED method)."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
import os

# ==================== RED METRICS ====================
# Request Rate, Error Rate, Duration (Latency)

# Request rate by method, endpoint, and status
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

# Request duration (latency) distribution
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# HTTP request errors
http_requests_errors_total = Counter(
    "http_requests_errors_total",
    "Total HTTP request errors",
    ["method", "endpoint", "error_type"],
)

# ==================== APPLICATION METRICS ====================

# User metrics
user_logins_total = Counter(
    "user_logins_total",
    "Total user login attempts",
    ["success"],
)

user_registrations_total = Counter(
    "user_registrations_total",
    "Total user registrations",
)

# Task metrics
tasks_created_total = Counter(
    "tasks_created_total",
    "Total tasks created",
)

tasks_completed_total = Counter(
    "tasks_completed_total",
    "Total tasks completed",
)

tasks_deleted_total = Counter(
    "tasks_deleted_total",
    "Total tasks deleted",
)

active_tasks_gauge = Gauge(
    "active_tasks_total",
    "Total active tasks",
)

# Reminder metrics
reminders_created_total = Counter(
    "reminders_created_total",
    "Total reminders created",
)

# ==================== DATABASE METRICS ====================

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["operation", "table"],
    buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

database_errors_total = Counter(
    "database_errors_total",
    "Total database errors",
    ["operation", "error_type"],
)

# ==================== AUTHENTICATION METRICS ====================

auth_failures_total = Counter(
    "auth_failures_total",
    "Total authentication failures",
    ["reason"],  # invalid_credentials, user_not_found, user_inactive, etc.
)

jwt_token_issued_total = Counter(
    "jwt_token_issued_total",
    "Total JWT tokens issued",
    ["token_type"],  # access, refresh
)

# ==================== RATE LIMITING METRICS ====================

rate_limit_exceeded_total = Counter(
    "rate_limit_exceeded_total",
    "Total rate limit exceeded events",
)

# ==================== HEALTH CHECK METRICS ====================

health_check_status = Gauge(
    "health_check_status",
    "Health check status (1=healthy, 0=unhealthy)",
    ["check_type"],  # database, redis, etc.
)

app_startup_time_seconds = Gauge(
    "app_startup_time_seconds",
    "Application startup time in seconds",
)

# ==================== UTILITY FUNCTIONS ====================


def get_metrics_as_bytes():
    """Get Prometheus metrics as bytes for /metrics endpoint."""
    return generate_latest()
