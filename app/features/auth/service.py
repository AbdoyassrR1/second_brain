#!/usr/bin/python3
"""Auth service for business logic."""

import re
import secrets
from datetime import datetime, timedelta, UTC
from flask import current_app, g, request
from flask_jwt_extended import create_access_token
from app.shared.exceptions import (
    ValidationError,
    UnauthorizedError,
    ConflictError,
    NotFoundError,
    ForbiddenError,
)
from app.shared.logging.audit_log import (
    log_registration,
    log_login_attempt,
    log_profile_update,
    log_logout,
    log_auth_failure,
    log_password_reset_requested,
    log_password_reset_completed,
    log_password_changed,
    log_account_locked,
    log_account_deleted,
    log_device_login,
    log_otp_sent,
    log_otp_verified,
    log_otp_failed,
    log_2fa_enabled,
    log_2fa_disabled,
)
from app.shared.database import database
from .repository import (
    UserRepository,
    RoleRepository,
    VerificationTokenRepository,
    ResetTokenRepository,
    TokenBlocklistRepository,
    UserDeviceRepository,
)
from app.features.mail.service import MailService

# ── Password-strength pattern: ≥8 chars, ≥1 uppercase, ≥1 lowercase, ≥1 digit ──
_PASSWORD_STRENGTH_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def validate_password_strength(password):
    """Raise ValidationError if the password does not meet strength rules."""
    if not _PASSWORD_STRENGTH_RE.match(password):
        raise ValidationError(
            "Password must be at least 8 characters and contain at least "
            "one uppercase letter, one lowercase letter, and one digit."
        )


class AuthService:
    """Service for authentication and user management."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.role_repo = RoleRepository()
        self.mail_service = MailService()
        self.verification_token_repo = VerificationTokenRepository()
        self.reset_token_repo = ResetTokenRepository()
        self.token_blocklist_repo = TokenBlocklistRepository()
        self.device_repo = UserDeviceRepository()

    # ── Registration ────────────────────────────────────────────────

    def register(self, username, email, password, phone_number, role="customer"):
        """Register a new user.

        Args:
            username: Unique username
            email: Unique email
            password: Plain text password (will be hashed)
            phone_number: Unique phone number
            role: User role (default is "customer")

        Returns:
            User object

        Raises:
            ValidationError: If input is invalid
            ConflictError: If username/email/phone already exists
        """

        # Check for duplicates
        if self.user_repo.find_by_username(username):
            raise ConflictError("Username already exists")
        if self.user_repo.find_by_email(email):
            raise ConflictError("Email already exists")
        if self.user_repo.find_by_phone_number(phone_number):
            raise ConflictError("Phone number already exists")

        validate_password_strength(password)

        # Get default role
        role_record = self.role_repo.find_by_name(role)
        if not role_record:
            raise NotFoundError(f"Role '{role}' not found")

        # Create user
        user = self.user_repo.create(username, email, password, phone_number, role_record.id)

        # Log registration audit event
        log_registration(user.id, username, email)

        # Send verification email after creating the account.
        self.send_email_verification(email)

        return user

    # ── Email Verification ────────────────────────────────────────────

    def _issue_verification_token(self, user, recipient_email=None):
        """Create and send a verification token for a user."""
        token = secrets.token_urlsafe(32)
        expiry_minutes = current_app.config.get("EMAIL_VERIFICATION_TOKEN_EXPIRES_MINUTES", 30)
        expiry_date = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

        self.verification_token_repo.invalidate_user_tokens(user.id)
        self.verification_token_repo.create(user.id, token, expiry_date)
        self.mail_service.send_email_verification(user, token, recipient_email=recipient_email)
        return user

    def send_email_verification(self, email):
        """Send email verification for an existing user.

        Returns:
            User object

        Raises:
            NotFoundError: If user is not found
            ConflictError: If user is already verified
        """
        user = self.user_repo.find_by_email(email)
        if not user:
            # Silent ignore — no enumeration
            return None

        if user.is_verified:
            raise ConflictError("Email is already verified")

        return self._issue_verification_token(user)

    def verify_email(self, token):
        """Verify a user's email address using a verification token."""
        verification_token = self.verification_token_repo.find_active_by_token(token)
        if not verification_token:
            raise NotFoundError("Invalid or expired verification token")

        user = verification_token.user
        if not user:
            raise NotFoundError("User not found")

        if user.pending_email:
            user.email = user.pending_email
            user.pending_email = None

        user.is_verified = True
        user.verified_at = datetime.now(UTC)
        verification_token.is_used = True
        database.commit()

        return user

    # ── Login (with lockout + device tracking) ───────────────────────

    def login(self, password, email=None, username=None):
        """Authenticate user and return user object.

        Implements account lockout after ``MAX_FAILED_LOGIN_ATTEMPTS``
        consecutive failures and records the login device.

        Returns:
            User object if authentication successful

        Raises:
            UnauthorizedError: If credentials are invalid or account is locked
        """
        from app.shared.metrics import user_logins_total, auth_failures_total

        identity = email or username
        if email:
            user = self.user_repo.find_by_email(email)
        else:
            user = self.user_repo.find_by_username(username)

        if not user:
            log_auth_failure(identity, "user_not_found")
            auth_failures_total.labels(reason="user_not_found").inc()
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("Invalid email or password")

        # ── Account lockout check ──
        locked_until = user.locked_until
        if locked_until is not None and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)
        if locked_until and locked_until > datetime.now(UTC):
            log_auth_failure(identity, "account_locked")
            auth_failures_total.labels(reason="account_locked").inc()
            user_logins_total.labels(success="false").inc()
            remaining = (locked_until - datetime.now(UTC)).seconds
            raise UnauthorizedError(
                f"Account temporarily locked. Try again in {remaining} seconds."
            )

        if not user.check_password(password):
            failed = self.user_repo.increment_failed_attempts(user.id)
            max_attempts = current_app.config.get("MAX_FAILED_LOGIN_ATTEMPTS", 5)

            if failed >= max_attempts:
                lockout_minutes = current_app.config.get("ACCOUNT_LOCKOUT_MINUTES", 15)
                locked_until = datetime.now(UTC) + timedelta(minutes=lockout_minutes)
                self.user_repo.lock_account(user.id, locked_until)
                log_account_locked(user.id, locked_until)
                from app.shared.metrics import account_lockouts_total
                account_lockouts_total.inc()

            log_login_attempt(identity, False, reason="invalid_password")
            auth_failures_total.labels(reason="invalid_password").inc()
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("Invalid email or password")

        if not user.is_active:
            log_login_attempt(identity, False, reason="user_inactive")
            auth_failures_total.labels(reason="user_inactive").inc()
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("User account is inactive")

        if not user.is_verified:
            log_login_attempt(identity, False, reason="user_not_verified")
            auth_failures_total.labels(reason="user_not_verified").inc()
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("User account is not verified")

        # ── Successful login ──
        self.user_repo.reset_failed_attempts(user.id)

        user.last_login = datetime.now(UTC)
        database.commit()

        # Record device
        self._capture_device(user.id)

        log_login_attempt(identity, True)
        user_logins_total.labels(success="true").inc()
        
        # If 2FA is enabled, generate an OTP and return a pending token
        if user.two_factor_enabled:
            otp_code = user.generate_otp()
            database.commit()
            self.mail_service.send_otp_email(user, otp_code)
            log_otp_sent(user.id, user.email)
            pending_token = create_access_token(
                identity=user,
                expires_delta=timedelta(minutes=current_app.config.get("TWO_FACTOR_PENDING_TOKEN_EXPIRES_MINUTES", 5)),
                additional_claims={
                    "role": user.role.name if user.role else None,
                    "ver": user.token_version,
                    "2fa_pending": True,
                },
            )
            return {"status": "2fa_required", "pending_token": pending_token}

        return user

    def verify_otp(self, user_id, otp_code):
        """Verify a pending OTP for 2FA login."""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            log_otp_failed(user_id, "user_not_found")
            raise NotFoundError("User not found")

        if not user.verify_otp(otp_code):
            log_otp_failed(user.id, "invalid_or_expired_otp")
            raise UnauthorizedError("Invalid or expired OTP")

        user.otp_code = None
        user.otp_expiry = None
        database.commit()
        log_otp_verified(user.id, user.email)
        return user

    def enable_2fa(self, user_id, current_password):
        """Enable 2FA after confirming the current password."""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not user.check_password(current_password):
            raise UnauthorizedError("Current password is incorrect")

        if user.two_factor_enabled:
            raise ConflictError("Two-factor authentication is already enabled")

        user.two_factor_enabled = True
        database.commit()
        self.revoke_all_tokens(user.id)
        log_2fa_enabled(user.id)
        return user

    def disable_2fa(self, user_id, current_password):
        """Disable 2FA after confirming the current password."""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not user.check_password(current_password):
            raise UnauthorizedError("Current password is incorrect")

        if not user.two_factor_enabled:
            raise ConflictError("Two-factor authentication is not enabled")

        user.two_factor_enabled = False
        user.otp_code = None
        user.otp_expiry = None
        database.commit()
        self.revoke_all_tokens(user.id)
        log_2fa_disabled(user.id)
        return user

    # ── Logout / Token revocation ─────────────────────────────────────

    def revoke_token(self, jti, token_type, user_id, expires_at):
        """Revoke a single token by its jti (logout / rotation)."""
        self.token_blocklist_repo.create(jti, token_type, user_id, expires_at)
        log_logout(user_id)

    def revoke_all_tokens(self, user_id):
        """Invalidate ALL outstanding tokens for a user (logout-all / delete).

        Implemented by bumping the user's ``token_version``: every token carries
        the version it was minted at, and the blocklist loader rejects any token
        whose version no longer matches. This catches tokens we never saw the jti
        of (e.g. issued to other devices) — something a pure jti blocklist can't.
        """
        self.user_repo.bump_token_version(user_id)
        log_logout(user_id)

    # ── Refresh token rotation ─────────────────────────────────────────

    def rotate_refresh_token(self, user_id, old_jti, old_expires_at):
        """Revoke the old refresh token and return the user for new token minting."""
        self.token_blocklist_repo.create(old_jti, "refresh", user_id, old_expires_at)
        from app.shared.metrics import jwt_token_issued_total
        jwt_token_issued_total.labels(token_type="refresh_rotated").inc()

        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    # ── Password reset (forgot password) ─────────────────────────────

    def request_password_reset(self, email):
        """Request a password reset email.

        Always returns ``None`` (success) to avoid user-enumeration.
        If the email is unknown the request is silently ignored.
        """
        user = self.user_repo.find_by_email(email)
        if not user:
            # Silent ignore — no enumeration
            return None

        token = secrets.token_urlsafe(32)
        expiry_minutes = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", 15)
        expiry_date = datetime.now(UTC) + timedelta(minutes=expiry_minutes)

        self.reset_token_repo.invalidate_user_tokens(user.id)
        self.reset_token_repo.create(user.id, token, expiry_date)
        self.mail_service.send_password_reset_email(user, token)

        log_password_reset_requested(user.id, email)
        return None

    def reset_password(self, token, new_password):
        """Reset a user's password using a valid reset token.

        Raises:
            NotFoundError: If the token is invalid or expired.
            ValidationError: If the new password is too weak.
        """
        validate_password_strength(new_password)

        reset_token = self.reset_token_repo.find_active_by_token(token)
        if not reset_token:
            raise NotFoundError("Invalid or expired reset token")

        user = reset_token.user
        if not user or user.is_deleted:
            raise NotFoundError("User not found")

        user.set_password(new_password)
        reset_token.is_used = True
        # Unlock account and reset failed attempts so the user can log in.
        user.failed_attempts = 0
        user.locked_until = None
        database.commit()

        self.mail_service.send_password_changed_notification(user)
        log_password_reset_completed(user.id)
        from app.shared.metrics import password_resets_total
        password_resets_total.inc()

        return user

    # ── Change password while logged in ──────────────────────────────

    def change_password(self, user_id, current_password, new_password):
        """Change a user's password given the current password.

        Raises:
            NotFoundError: If the user does not exist.
            UnauthorizedError: If the current password is incorrect.
            ValidationError: If the new password is too weak or same as current.
        """
        validate_password_strength(new_password)

        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not user.check_password(current_password):
            raise UnauthorizedError("Current password is incorrect")

        if user.check_password(new_password):
            raise ValidationError("New password must be different from current password")

        user.set_password(new_password)
        database.commit()

        # Force re-login by revoking all tokens.
        self.revoke_all_tokens(user_id)

        self.mail_service.send_password_changed_notification(user)
        log_password_changed(user_id)

        return user

    def change_email(self, user_id, current_password, new_email):
        """Change email while keeping the current email active until verified."""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not user.check_password(current_password):
            raise UnauthorizedError("Current password is incorrect")

        if new_email == user.email:
            raise ValidationError("New email must be different from current email")

        if self.user_repo.find_by_email(new_email) or self.user_repo.find_by_pending_email(new_email):
            raise ConflictError("Email already exists")

        user.pending_email = new_email
        database.commit()

        self._issue_verification_token(user, recipient_email=new_email)
        log_profile_update(user_id, {"pending_email": new_email})

        return user

    # ── Profile / Account management ──────────────────────────────────

    def get_user_profile(self, user_id):
        """Get user profile by ID.

        Raises:
            NotFoundError: If user not found
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def update_user_profile(self, user_id, **kwargs):
        """Update user profile fields.

        Fields that are never allowed here: password, email, pending_email,
        role_id, is_verified, is_deleted. Password changes go through
        ``change_password``; email changes go through ``change_email``.

        Raises:
            NotFoundError: If user not found
            ConflictError: If username/email/phone already taken
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Guard fields that must never be mutated through this path.
        forbidden = {
            "password",
            "email",
            "pending_email",
            "role_id",
            "is_verified",
            "is_deleted",
            "failed_attempts",
            "locked_until",
        }
        for field in forbidden:
            if field in kwargs:
                if field in {"email", "pending_email"}:
                    raise ForbiddenError("Email changes must use /me/change-email")
                elif field == "password":
                    raise ForbiddenError("Password changes must use /me/change-password")
                else:
                    raise ForbiddenError(f"Field '{field}' cannot be updated via this endpoint")

        # Username uniqueness
        if "username" in kwargs and kwargs["username"] != user.username:
            if self.user_repo.find_by_username(kwargs["username"]):
                raise ConflictError("Username already exists")

        # Email uniqueness — when email changes, require re-verification.
        email_changed = "email" in kwargs and kwargs["email"] != user.email
        if email_changed:
            if self.user_repo.find_by_email(kwargs["email"]):
                raise ConflictError("Email already exists")

        # Phone uniqueness
        if "phone_number" in kwargs and kwargs["phone_number"] != user.phone_number:
            if self.user_repo.find_by_phone_number(kwargs["phone_number"]):
                raise ConflictError("Phone number already exists")

        updated_user = self.user_repo.update(user_id, **kwargs)
        log_profile_update(user_id, kwargs)

        return updated_user

    def delete_account(self, user_id):
        """Soft-delete the current user's account.

        Revokes all tokens so the user is immediately logged out.
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        self.user_repo.soft_delete(user_id)
        self.revoke_all_tokens(user_id)
        log_account_deleted(user_id)

        return user

    # ── Device tracking ──────────────────────────────────────────────

    def list_devices(self, user_id, page=1, per_page=20):
        return self.device_repo.find_by_user(user_id, page=page, per_page=per_page)

    def revoke_device(self, user_id, device_id):
        """Revoke a specific device."""
        if not self.device_repo.delete(device_id, user_id):
            raise NotFoundError("Device not found")
        return True

    # ── Internal helpers ─────────────────────────────────────────────

    def _capture_device(self, user_id):
        """Record the caller's device info from the current request context."""
        user_agent = request.headers.get("User-Agent", "") if request else ""
        ip_address = request.remote_addr if request else None
        # Best-effort device name from User-Agent; empty string is a valid key.
        device_name = user_agent[:120] if user_agent else None
        try:
            self.device_repo.upsert(
                user_id=user_id,
                device_name=device_name,
                user_agent=user_agent,
                ip_address=ip_address,
            )
            log_device_login(user_id, device_name, ip_address)
        except Exception:
            # Device capture must never break a login.
            pass
