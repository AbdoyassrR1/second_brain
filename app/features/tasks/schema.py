#!/usr/bin/python3
"""Tasks schemas for validation and serialization."""

from marshmallow import Schema, fields, validate
from app.shared.fields import UTCDateTime


class TaskCreateSchema(Schema):
    """Schema for creating a task."""

    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    status = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["todo", "in_progress", "completed", "cancelled"]),
    )
    priority = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["low", "medium", "high", "urgent"]),
    )
    due_date = fields.Date(allow_none=True)
    project_id = fields.Str(allow_none=True)
    parent_task_id = fields.Str(allow_none=True)


class TaskUpdateSchema(Schema):
    """Schema for updating a task."""

    title = fields.Str(validate=validate.Length(min=1, max=200), allow_none=True)
    description = fields.Str(allow_none=True)
    status = fields.Str(
        validate=validate.OneOf(["todo", "in_progress", "completed", "cancelled"]),
        allow_none=True,
    )
    priority = fields.Str(
        validate=validate.OneOf(["low", "medium", "high", "urgent"]),
        allow_none=True,
    )
    due_date = fields.Date(allow_none=True)
    project_id = fields.Str(allow_none=True)
    parent_task_id = fields.Str(allow_none=True)


class TaskResponseSchema(Schema):
    """Schema for task response."""

    id = fields.Str(dump_only=True)
    title = fields.Str()
    description = fields.Str(allow_none=True)
    status = fields.Str()
    priority = fields.Str()
    due_date = fields.Date(allow_none=True)
    completed_at = UTCDateTime(allow_none=True)
    is_archived = fields.Bool()
    archived_at = UTCDateTime(allow_none=True)
    is_deleted = fields.Bool(dump_only=True)
    deleted_at = UTCDateTime(allow_none=True, dump_only=True)
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)
    user_id = fields.Str()
    project_id = fields.Str(allow_none=True)
    parent_task_id = fields.Str(allow_none=True)
    labels = fields.List(fields.Nested("LabelRefSchema"), dump_only=True)


class LabelRefSchema(Schema):
    """Minimal label reference schema for embedding in task responses."""

    id = fields.Str()
    name = fields.Str()
    color = fields.Str(allow_none=True)


class BulkTaskActionSchema(TaskUpdateSchema):
    """Schema for bulk task operations."""

    task_ids = fields.List(fields.Str(), required=True, validate=validate.Length(min=1))


class StatisticsResponseSchema(Schema):
    """Schema for statistics response."""

    total_tasks = fields.Int()
    active_tasks = fields.Int()
    completed_tasks = fields.Int()
    archived_tasks = fields.Int()
    overdue_tasks = fields.Int()
    due_today_tasks = fields.Int()
    tasks_by_status = fields.Dict()
    tasks_by_priority = fields.Dict()
    completion_rate = fields.Float()