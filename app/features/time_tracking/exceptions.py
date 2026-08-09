#!/usr/bin/python3
"""Time tracking feature exceptions."""

from app.shared.exceptions import AppError


class TaskNotValidError(AppError):
    """Raised when task_ids contain nonexistent/foreign/deleted/archived ids."""

    def __init__(self, offenders):
        super().__init__(
            "Some task ids are invalid",
            status_code=404,
            error_code="TASK_NOT_VALID",
            errors={"task_ids": offenders},
        )


class TimerAlreadyRunningError(AppError):
    """Raised when starting a timer while one is already running."""

    def __init__(self):
        super().__init__(
            "A timer is already running",
            status_code=409,
            error_code="TIMER_ALREADY_RUNNING",
        )


class TimerNotRunningError(AppError):
    """Raised when a timer operation requires a running timer."""

    def __init__(self):
        super().__init__(
            "No timer is currently running",
            status_code=404,
            error_code="TIMER_NOT_RUNNING",
        )


class LastTaskRemovalDeniedError(AppError):
    """Raised when removing the last task link from a running timer."""

    def __init__(self):
        super().__init__(
            "A time entry must have at least one task; stop the timer or add another task first",
            status_code=400,
            error_code="LAST_TASK_REMOVAL_DENIED",
        )


class TaskNotInTimerError(AppError):
    """Raised when a task is not linked to the running timer."""

    def __init__(self):
        super().__init__(
            "Task is not linked to the running timer",
            status_code=404,
            error_code="TASK_NOT_IN_TIMER",
        )


class EntryIsRunningError(AppError):
    """Raised when mutating a running entry via the manual-entry endpoints."""

    def __init__(self):
        super().__init__(
            "Running entries cannot be edited; stop the timer first",
            status_code=409,
            error_code="ENTRY_IS_RUNNING",
        )


class EntryAlreadyStoppedError(AppError):
    """Raised when a conditional stop update matches no running row."""

    def __init__(self):
        super().__init__(
            "This timer has already been stopped",
            status_code=409,
            error_code="ENTRY_ALREADY_STOPPED",
        )


class InvalidTimeRangeError(AppError):
    """Raised when a time range (list filter / report) is invalid."""

    def __init__(self, message):
        super().__init__(message, status_code=400, error_code="INVALID_TIME_RANGE")


class TaskInRunningTimerError(AppError):
    """Raised by the tasks feature when deleting/archiving a task with a running link."""

    def __init__(self, task_ids, time_entry_id):
        super().__init__(
            "Task is linked to a running timer; stop the timer or remove the task from it first",
            status_code=409,
            error_code="TASK_IN_RUNNING_TIMER",
            errors={"task_ids": list(task_ids), "time_entry_id": time_entry_id},
        )
