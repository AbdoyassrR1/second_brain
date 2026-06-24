#!/usr/bin/python3
"""Auth schemas for validation and serialization."""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError

# Reusable strength validator: ≥8 chars, ≥1 lower, ≥1 upper, ≥1 digit.
PASSWORD_STRENGTH = [
    validate.Length(min=8, error="Password must be at least 8 characters."),
    validate.Regexp(
        r"(?=.*[a-z])",
        error="Password must contain at least one lowercase letter.",
    ),
    validate.Regexp(
        r"(?=.*[A-Z])",
        error="Password must contain at least one uppercase letter.",
    ),
    validate.Regexp(
        r"(?=.*\d)",
        error="Password must contain at least one digit.",
    ),
]


class RoleSchema(Schema):
    """Role schema."""

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    description = fields.Str(required=True)


class UserRegistrationSchema(Schema):
    """Schema for user registration."""

    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=PASSWORD_STRENGTH, load_only=True)
    phone_number = fields.Str(required=True)


class UserLoginSchema(Schema):
    """Schema for user login."""

    email = fields.Email(required=False, allow_none=True)
    username = fields.Str(required=False, allow_none=True)
    password = fields.Str(required=True, load_only=True)
    remember_me = fields.Bool(required=False, load_default=False)

    @validates_schema
    def validate_identity(self, data, **kwargs):
        if not data.get("email") and not data.get("username"):
            raise ValidationError("Either email or username is required")


class SendEmailVerificationSchema(Schema):
    """Schema for requesting a verification email."""

    email = fields.Email(required=True)


class VerifyEmailSchema(Schema):
    """Schema for verifying an email with a token."""

    token = fields.Str(required=True, validate=validate.Length(min=1))


class ForgotPasswordSchema(Schema):
    """Schema for the forgot-password request."""

    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    """Schema for completing a password reset."""

    token = fields.Str(required=True, validate=validate.Length(min=1))
    new_password = fields.Str(required=True, validate=PASSWORD_STRENGTH, load_only=True)


class ChangePasswordSchema(Schema):
    """Schema for changing password while logged in."""

    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, validate=PASSWORD_STRENGTH, load_only=True)


class ChangeEmailSchema(Schema):
    """Schema for changing email while logged in."""

    current_password = fields.Str(required=True, load_only=True)
    new_email = fields.Email(required=True)


class RefreshTokenSchema(Schema):
    """Schema for the refresh endpoint (body variant).

    The refresh token is normally read from the Authorization header, but
    accepting it in the body is a common convenience.
    """

    refresh_token = fields.Str(required=False, load_only=True)


class UpdateProfileSchema(Schema):
    """Schema for PATCH /me — all fields optional."""

    username = fields.Str(required=False, validate=validate.Length(min=3, max=50))
    phone_number = fields.Str(required=False)
    first_name = fields.Str(required=False, allow_none=True)
    last_name = fields.Str(required=False, allow_none=True)
    avatar = fields.Str(required=False, allow_none=True)
    birth_date = fields.Date(required=False, allow_none=True)
    gender = fields.Str(required=False, allow_none=True)
    country = fields.Str(required=False, allow_none=True)
    city = fields.Str(required=False, allow_none=True)


class UserProfileSchema(Schema):
    """Schema for user profile response."""

    id = fields.Str(dump_only=True)
    username = fields.Str()
    email = fields.Email()
    pending_email = fields.Email(allow_none=True)
    is_verified = fields.Bool()
    phone_number = fields.Str()
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    avatar = fields.Str(allow_none=True)
    birth_date = fields.Date(allow_none=True)
    gender = fields.Str(allow_none=True)
    country = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    is_active = fields.Bool()
    is_verified = fields.Bool()
    last_login = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    role_id = fields.Int()


class UserDeviceSchema(Schema):
    """Schema for a recorded device/session."""

    id = fields.Str(dump_only=True)
    device_name = fields.Str(allow_none=True)
    user_agent = fields.Str(allow_none=True)
    ip_address = fields.Str(allow_none=True)
    last_seen = fields.DateTime()
    created_at = fields.DateTime(dump_only=True)
