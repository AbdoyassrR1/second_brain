from datetime import datetime, UTC
from marshmallow import fields, ValidationError


class UTCDateTime(fields.DateTime):
    """Accepts naive datetimes (treated as UTC) and aware datetimes (converted to UTC).
    Always serializes with +00:00 timezone.
    """

    def _deserialize(self, value, attr, data, **kwargs):
        dt = super()._deserialize(value, attr, data, **kwargs)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return super()._serialize(value, attr, obj, **kwargs)
