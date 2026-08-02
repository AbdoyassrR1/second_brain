"""Shared Marshmallow schemas for query parameters."""

from marshmallow import Schema, fields


class PaginationQuerySchema(Schema):
    """Common pagination query parameters used by list endpoints."""

    page = fields.Int(load_default=1)
    per_page = fields.Int(load_default=20)
