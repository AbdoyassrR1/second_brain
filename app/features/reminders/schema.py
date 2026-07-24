from marshmallow import Schema, fields
from app.shared.fields import UTCDateTime


class ReminderSchema(Schema):
    id = fields.Str(dump_only=True)
    reminder_time = UTCDateTime(required=True)
    is_sent = fields.Int()
    task_id = fields.Str(required=True)
    user_id = fields.Str()
    created_at = UTCDateTime(dump_only=True)
    updated_at = UTCDateTime(dump_only=True)


class ReminderUpdateSchema(Schema):
    reminder_time = UTCDateTime()
