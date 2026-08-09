#!/usr/bin/python3
"""Time tracking schemas for validation and serialization."""

from marshmallow import Schema, fields, validate, ValidationError, validates_schema
from app.shared.schemas.fields import UTCDateTime
from app.shared.schemas.query_schemas import PaginationQuerySchema


def _task_ids_field():
    """1..10 required UUID task ids (service dedupes)."""
    return fields.List(
        fields.UUID(required=True),
        required=True,
        validate=validate.Length(min=1, max=10),
    )


class TimerStartSchema(Schema):
    """Schema for starting a timer."""

    task_ids = _task_ids_field()
    note = fields.Str(allow_none=True, validate=validate.Length(max=2000))


class TimerAddTasksSchema(Schema):
    """Schema for adding tasks to a running timer."""

    task_ids = _task_ids_field()


class TimeEntryCreateSchema(Schema):
    """Schema for creating a manual (completed) time entry."""

    task_ids = _task_ids_field()
    started_at = UTCDateTime(required=True)
    ended_at = UTCDateTime(required=True)
    note = fields.Str(allow_none=True, validate=validate.Length(max=2000))

    @validates_schema
    def _validate_range(self, data, **kwargs):
        if data["started_at"] >= data["ended_at"]:
            raise ValidationError({"ended_at": ["must be after started_at"]})


class TimeEntryUpdateSchema(Schema):
    """Schema for patching a time entry (partial)."""

    task_ids = fields.List(
        fields.UUID(required=True),
        validate=validate.Length(min=1, max=10),
        required=False,
    )
    started_at = UTCDateTime(required=False)
    ended_at = UTCDateTime(required=False)
    note = fields.Str(allow_none=True, validate=validate.Length(max=2000))


class TimeEntryListQuerySchema(PaginationQuerySchema):
    """Query params for listing time entries."""

    from_ = UTCDateTime(allow_none=True, data_key="from")
    to_ = UTCDateTime(allow_none=True, data_key="to")
    task_id = fields.UUID(allow_none=True)
    running = fields.Bool(allow_none=True)
    per_page = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))


class ReportQuerySchema(Schema):
    """Query params for the time report endpoint."""

    group_by = fields.Str(
        required=True,
        validate=validate.OneOf(["day", "week", "task", "project"]),
    )
    from_ = UTCDateTime(required=True, data_key="from")
    to_ = UTCDateTime(required=True, data_key="to")
    tz = fields.Str(load_default="UTC")


class TimeEntryTaskSchema(Schema):
    """Serialized task link inside a time entry."""

    task_id = fields.Str()
    task_title = fields.Str(allow_none=True)
    allocated_seconds = fields.Int(allow_none=True)
    is_deleted = fields.Bool()
    is_archived = fields.Bool()


class TimeEntryResponseSchema(Schema):
    """Serialized time entry (used for both timer and completed entry shapes)."""

    id = fields.Str(dump_only=True)
    user_id = fields.Str(dump_only=True)
    started_at = UTCDateTime(dump_only=True)
    ended_at = UTCDateTime(dump_only=True, allow_none=True)
    duration_seconds = fields.Int(dump_only=True, allow_none=True)
    running = fields.Bool(dump_only=True)
    note = fields.Str(dump_only=True, allow_none=True)
    task_links = fields.Nested(TimeEntryTaskSchema, many=True, dump_only=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class ReportResponseSchema(Schema):
    """Serialized report payload."""

    group_by = fields.Str(dump_only=True)
    tz = fields.Str(dump_only=True)
    from_ = UTCDateTime(dump_only=True, data_key="from")
    to_ = UTCDateTime(dump_only=True, data_key="to")
    totals = fields.Raw(dump_only=True)
    groups = fields.Raw(dump_only=True)
