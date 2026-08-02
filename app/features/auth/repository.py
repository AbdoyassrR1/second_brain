#!/usr/bin/python3
"""Auth repository for database operations."""

from datetime import datetime, UTC
from sqlalchemy import and_
from app.extensions import db
from .models import User, Role, VerificationToken, ResetToken, TokenBlocklist, UserDevice


class UserRepository:
    """Repository for User database operations."""

    @staticmethod
    def find_by_username(username, include_deleted=False):
        """Find a non-deleted user by username."""
        query = User.query.filter_by(username=username)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @staticmethod
    def find_by_email(email, include_deleted=False):
        """Find a non-deleted user by email."""
        query = User.query.filter_by(email=email)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @staticmethod
    def find_by_pending_email(pending_email, include_deleted=False):
        """Find a non-deleted user by pending email."""
        query = User.query.filter_by(pending_email=pending_email)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @staticmethod
    def find_by_phone_number(phone_number, include_deleted=False):
        """Find a non-deleted user by phone number."""
        query = User.query.filter_by(phone_number=phone_number)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @staticmethod
    def find_by_id(user_id, include_deleted=False):
        """Find a non-deleted user by ID."""
        query = User.query.filter_by(id=user_id)
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.first()

    @staticmethod
    def create(username, email, password, phone_number, role_id=1):
        """Create and save a new user."""
        user = User(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
            role_id=role_id,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(user_id, **kwargs):
        """Update user fields."""
        user = User.query.filter_by(id=user_id).first()
        if user and kwargs:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.updated_at = datetime.now(UTC)
            db.session.commit()
        return user

    @staticmethod
    def increment_failed_attempts(user_id):
        """Increment the failed-login counter and return the new value."""
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return 0
        user.failed_attempts = (user.failed_attempts or 0) + 1
        db.session.commit()
        return user.failed_attempts

    @staticmethod
    def lock_account(user_id, locked_until):
        """Lock a user account until the given datetime."""
        user = User.query.filter_by(id=user_id).first()
        if user:
            user.locked_until = locked_until
            db.session.commit()
        return user

    @staticmethod
    def reset_failed_attempts(user_id):
        """Reset failed-login counter and clear any lockout."""
        user = User.query.filter_by(id=user_id).first()
        if user:
            user.failed_attempts = 0
            user.locked_until = None
            db.session.commit()
        return user

    @staticmethod
    def soft_delete(user_id):
        """Soft-delete a user account (set tombstone)."""
        user = User.query.filter_by(id=user_id).first()
        if user:
            user.is_deleted = True
            user.deleted_at = datetime.now(UTC)
            db.session.commit()
        return user

    @staticmethod
    def bump_token_version(user_id):
        """Increment the user's token version, invalidating all outstanding tokens.

        Returns the new version, or ``None`` if the user does not exist.
        """
        user = User.query.filter_by(id=user_id).first()
        if not user:
            return None
        user.token_version = (user.token_version or 0) + 1
        db.session.commit()
        return user.token_version


class RoleRepository:
    """Repository for Role database operations."""

    @staticmethod
    def find_by_id(role_id):
        """Find role by ID."""
        return Role.query.filter_by(id=role_id).first()

    @staticmethod
    def find_by_name(name):
        """Find role by name."""
        return Role.query.filter_by(name=name).first()

    @staticmethod
    def create(name, description):
        """Create and save a new role."""
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
        return role

    @staticmethod
    def seed_default_roles():
        """Insert the default roles if they do not already exist."""

        roles = {
            "customer": "Standard user role",
            "admin": "Administrator role with full permissions",
        }

        inserted = 0
        for name, description in roles.items():
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=description))
                inserted += 1

        if inserted:
            db.session.commit()

        return inserted


class VerificationTokenRepository:
    """Repository for verification token database operations."""

    @staticmethod
    def create(user_id, token, expiry_date):
        """Create a verification token record."""
        verification_token = VerificationToken(
            user_id=user_id,
            token=token,
            expiry_date=expiry_date,
            is_used=False,
        )
        db.session.add(verification_token)
        db.session.commit()
        return verification_token

    @staticmethod
    def find_by_token(token):
        """Find a verification token by its value."""
        return VerificationToken.query.filter_by(token=token).first()

    @staticmethod
    def find_active_by_token(token):
        """Find an unused, unexpired verification token by value."""
        return VerificationToken.query.filter(
            and_(
                VerificationToken.token == token,
                VerificationToken.is_used.is_(False),
                VerificationToken.expiry_date > datetime.now(UTC),
            )
        ).first()

    @staticmethod
    def mark_used(token_record):
        """Mark a verification token as used."""
        if token_record:
            token_record.is_used = True
            db.session.commit()
        return token_record

    @staticmethod
    def invalidate_user_tokens(user_id):
        """Mark all unused verification tokens for a user as used."""
        tokens = VerificationToken.query.filter_by(user_id=user_id, is_used=False).all()
        for token in tokens:
            token.is_used = True
        if tokens:
            db.session.commit()
        return tokens


class ResetTokenRepository:
    """Repository for password-reset token database operations.

    Mirrors VerificationTokenRepository's contract so the reset flow
    looks identical to the verification flow at the service layer.
    """

    @staticmethod
    def create(user_id, token, expiry_date):
        """Create a reset token record."""
        reset_token = ResetToken(
            user_id=user_id,
            token=token,
            expiry_date=expiry_date,
            is_used=False,
        )
        db.session.add(reset_token)
        db.session.commit()
        return reset_token

    @staticmethod
    def find_by_token(token):
        """Find a reset token by its value."""
        return ResetToken.query.filter_by(token=token).first()

    @staticmethod
    def find_active_by_token(token):
        """Find an unused, unexpired reset token by value."""
        return ResetToken.query.filter(
            and_(
                ResetToken.token == token,
                ResetToken.is_used.is_(False),
                ResetToken.expiry_date > datetime.now(UTC),
            )
        ).first()

    @staticmethod
    def mark_used(token_record):
        """Mark a reset token as used."""
        if token_record:
            token_record.is_used = True
            db.session.commit()
        return token_record

    @staticmethod
    def invalidate_user_tokens(user_id):
        """Mark all unused reset tokens for a user as used."""
        tokens = ResetToken.query.filter_by(user_id=user_id, is_used=False).all()
        for token in tokens:
            token.is_used = True
        if tokens:
            db.session.commit()
        return tokens


class TokenBlocklistRepository:
    """Repository for revoked JWT entries (logout / refresh rotation)."""

    @staticmethod
    def create(jti, token_type, user_id, expires_at):
        """Record a revoked token (idempotent on jti)."""
        existing = TokenBlocklist.query.filter_by(jti=jti).first()
        if existing:
            return existing
        entry = TokenBlocklist(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @staticmethod
    def is_revoked(jti):
        """Return True if the given jti has been revoked."""
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None


class UserDeviceRepository:
    """Repository for login device/session tracking."""

    @staticmethod
    def upsert(user_id, device_name=None, user_agent=None, ip_address=None):
        """Insert or refresh the last_seen/ip for a (user, device_name) pair.

        Devices are keyed by (user_id, device_name) so repeated logins from
        the same named device update rather than duplicate.
        """
        device = UserDevice.query.filter_by(
            user_id=user_id, device_name=device_name
        ).first()
        now = datetime.now(UTC)
        if device is None:
            device = UserDevice(
                user_id=user_id,
                device_name=device_name,
                user_agent=user_agent,
                ip_address=ip_address,
                last_seen=now,
            )
            db.session.add(device)
        else:
            device.user_agent = user_agent or device.user_agent
            device.ip_address = ip_address or device.ip_address
            device.last_seen = now
        db.session.commit()
        return device

    @staticmethod
    def find_by_user(user_id, page=1, per_page=20):
        query = UserDevice.query.filter_by(user_id=user_id).order_by(UserDevice.last_seen.desc())
        return db.paginate(query, page=page, per_page=per_page, error_out=False)

    @staticmethod
    def delete(device_id, user_id):
        """Delete a specific device record for a user."""
        device = UserDevice.query.filter_by(id=device_id, user_id=user_id).first()
        if device:
            db.session.delete(device)
            db.session.commit()
            return True
        return False
