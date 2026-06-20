#!/usr/bin/python3
"""Auth schemas for validation and serialization."""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError


class RoleSchema(Schema):
    """Role schema."""

    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    description = fields.Str(required=True)


class UserRegistrationSchema(Schema):
    """Schema for user registration."""

    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8), load_only=True)
    phone_number = fields.Str(required=True)


class UserLoginSchema(Schema):
    """Schema for user login."""

    email = fields.Email(required=False, allow_none=True)
    username = fields.Str(required=False, allow_none=True)
    password = fields.Str(required=True, load_only=True)

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

class UserProfileSchema(Schema):
    """Schema for user profile response."""

    id = fields.Str(dump_only=True)
    username = fields.Str()
    email = fields.Email()
    phone_number = fields.Str()
    first_name = fields.Str(allow_none=True)
    last_name = fields.Str(allow_none=True)
    avatar = fields.Str(allow_none=True)
    birth_date = fields.Date(allow_none=True)
    gender = fields.Str(allow_none=True)
    country = fields.Str(allow_none=True)
    city = fields.Str(allow_none=True)
    is_active = fields.Bool()
    last_login = fields.DateTime(allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    role_id = fields.Int()
