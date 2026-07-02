#!/usr/bin/python3
"""Labels schemas for validation and serialization."""

from marshmallow import Schema, fields, validate


class LabelCreateSchema(Schema):
    """Schema for creating a label."""

    name = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    color = fields.Str(allow_none=True, validate=validate.Length(min=4, max=7))


class LabelResponseSchema(Schema):
    """Schema for label response."""

    id = fields.Str(dump_only=True)
    name = fields.Str()
    color = fields.Str(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    user_id = fields.Str()