from marshmallow import Schema, fields, validate
from app.shared.schemas.fields import UTCDateTime
from app.shared.schemas.query_schemas import PaginationQuerySchema


class ReminderSchema(Schema):
    id = fields.Str(dump_only=True)
    reminder_time = UTCDateTime(required=True)
    is_sent = fields.Str()
    task_id = fields.Str(required=True)
    user_id = fields.Str()
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class ReminderUpdateSchema(Schema):
    reminder_time = UTCDateTime()


class ReminderListQuerySchema(PaginationQuerySchema):
    status = fields.Str(
        validate=validate.OneOf(["pending", "sent", "failed"]),
        allow_none=True,
    )
