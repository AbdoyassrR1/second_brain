from marshmallow import Schema, fields


class ReminderSchema(Schema):
    id = fields.Str(dump_only=True)
    reminder_time = fields.DateTime(required=True)
    is_sent = fields.Int()
    task_id = fields.Str(required=True)
    user_id = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class ReminderUpdateSchema(Schema):
    reminder_time = fields.DateTime()
