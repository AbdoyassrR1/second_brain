#!/usr/bin/python3
"""Projects schemas for validation and serialization."""

from marshmallow import Schema, fields, validate


class ProjectCreateSchema(Schema):
    """Schema for creating a project."""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True, validate=validate.Length(min=4, max=7))


class ProjectUpdateSchema(Schema):
    """Schema for updating a project."""

    name = fields.Str(validate=validate.Length(min=1, max=200), allow_none=True)
    description = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True, validate=validate.Length(min=4, max=7))


class ProjectResponseSchema(Schema):
    """Schema for project response."""

    id = fields.Str(dump_only=True)
    name = fields.Str()
    description = fields.Str(allow_none=True)
    color = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    user_id = fields.Str()