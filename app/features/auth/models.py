#!/usr/bin/python3
"""Auth feature models: User and Role."""

import random

from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text, Date, Integer, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
from app.extensions import bcrypt, db
from app.shared.models import BaseModel


class Role(BaseModel):
    """Role model for RBAC."""

    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(30), nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # one-to-many Relationships
    users = relationship("User", backref="role")

    def __repr__(self):
        return f"<Role ID: {self.id}, Role Name: {self.name}>"


class User(BaseModel):
    """User model."""

    __tablename__ = "users"

    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True) # 255 to accommodate long emails (RFC 5321)
    pending_email = Column(String(255), nullable=True)
    password = Column(String(255), nullable=False)
    otp_code = Column(String(6), nullable=True)
    otp_expiry = Column(DateTime, nullable=True)
    phone_number = Column(String(20), nullable=False, unique=True)
    first_name = Column(String(20), nullable=True)
    last_name = Column(String(20), nullable=True)
    avatar = Column(Text, nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(Enum("MALE", "FEMALE", name="gender"), nullable=True)
    country = Column(String(15), nullable=True)
    city = Column(String(20), nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime, default=lambda: datetime.now(), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now())

    # Account security / lockout
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    # Soft delete tombstone (account deletion)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # ForeignKeys
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    # one-to-many Relationships
    reset_tokens = relationship("ResetToken", backref="user")
    verification_tokens = relationship("VerificationToken", backref="user")
    devices = relationship("UserDevice", backref="user")

    def __repr__(self):
        return f"<Username: {self.username}, Email: {self.email}>"

    def set_password(self, password):
        """Hash and set password."""
        self.password = bcrypt.generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash."""
        return bcrypt.check_password_hash(self.password, password)
    
    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))  # 6-digit code
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=5)  # valid for 5 minutes
        return self.otp_code

    def verify_otp(self, code):
        return self.otp_code == code and self.otp_expiry and self.otp_expiry > datetime.utcnow()


class ResetToken(db.Model):
    """Password reset token model."""

    __tablename__ = "reset_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(260), nullable=False, unique=True)
    timestamp = Column(DateTime, default=lambda: datetime.now())
    is_used = Column(Boolean, default=False, nullable=False)
    expiry_date = Column(DateTime, nullable=False)

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    def set_expiry_date(self, minutes):
        """Set token expiration."""
        self.timestamp = datetime.now()
        self.expiry_date = self.timestamp + timedelta(minutes=minutes)


class VerificationToken(db.Model):
    """Verification token model."""

    __tablename__ = "verification_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(260), nullable=False, unique=True)
    timestamp = Column(DateTime, default=lambda: datetime.now())
    is_used = Column(Boolean, default=False, nullable=False)
    expiry_date = Column(DateTime, nullable=False)

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    def set_expiry_date(self, minutes):
        """Set token expiration."""
        self.timestamp = datetime.now()
        self.expiry_date = self.timestamp + timedelta(minutes=minutes)


class TokenBlocklist(db.Model):
    """Revoked JWT entries (logout / refresh rotation / account deletion).

    Keyed on the JWT `jti` claim. Mirrors the token-table convention
    (Integer PK) used by ResetToken/VerificationToken.
    """

    __tablename__ = "token_blocklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(36), nullable=False, unique=True, index=True)
    token_type = Column(String(10), nullable=False)  # "access" or "refresh"
    created_at = Column(DateTime, default=lambda: datetime.now())
    # When the original token would have naturally expired — safe to purge after this.
    expires_at = Column(DateTime, nullable=False)

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)

class UserDevice(BaseModel):
    """A device/session fingerprint recorded at login for tracking."""

    __tablename__ = "user_devices"

    device_name = Column(String(120), nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6-capable
    last_seen = Column(DateTime, default=lambda: datetime.now())

    # ForeignKeys
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
