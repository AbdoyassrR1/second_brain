#!/usr/bin/python3
"""Tests for auth service business logic."""

import pytest
from datetime import timedelta, UTC

from app.extensions import db as _db
from app.features.auth.service import AuthService, validate_password_strength
from app.shared.exceptions import (
    ValidationError,
    ConflictError,
    UnauthorizedError,
    NotFoundError,
)
from app.features.auth.repository import ResetTokenRepository


class TestAuthService:
    """Test auth service."""

    def test_register_user(self, db):
        """Test user registration through service."""
        service = AuthService()
        user = service.register(
            username="servicetest",
            email="service@test.com",
            password="Password123",
            phone_number="5555555555",
        )

        assert user is not None
        assert user.username == "servicetest"

    def test_register_duplicate_username(self, db):
        """Test registration rejects duplicate username."""
        service = AuthService()
        service.register(
            username="existing",
            email="first@test.com",
            password="Password123",
            phone_number="1111111111",
        )

        with pytest.raises(ConflictError):
            service.register(
                username="existing",
                email="second@test.com",
                password="Password123",
                phone_number="2222222222",
            )

    def test_login_success(self, db, verified_user):
        """Test successful login."""
        service = AuthService()
        user = service.login(username=verified_user.username, password="Password123")
        assert user.username == verified_user.username

    def test_login_survives_device_capture_failure(self, app, db, verified_user, monkeypatch):
        """Login must succeed even if device capture fails, without poisoning the session.

        Regression test: a failed commit during device upsert used to leave the
        session in a broken (pending rollback) state, breaking the rest of the
        request. The centralized ``database.commit()`` rolls back before re-raising,
        so a swallowed failure must leave the session usable.
        """
        from datetime import datetime, UTC
        from app.features.auth.models import User
        from app.shared.database import database

        def failing_upsert(user_id, device_name=None, user_agent=None, ip_address=None):
            _db.session.add(
                User(
                    username="duplicate",
                    email=verified_user.email,
                    password="x",
                    phone_number="0000000000",
                )
            )
            database.commit()

        service = AuthService()
        monkeypatch.setattr(service.device_repo, "upsert", failing_upsert)

        with app.test_request_context():
            user = service.login(username=verified_user.username, password="Password123")

        assert user.username == verified_user.username

        verified_user.last_login = datetime.now(UTC)
        database.commit()
        _db.session.expire_all()
        assert verified_user.last_login is not None

    def test_login_with_2fa_returns_pending_token(self, db, verified_user, monkeypatch):
        """Test login returns a 2FA pending token when enabled."""
        service = AuthService()
        verified_user.two_factor_enabled = True
        _db.session.commit()

        captured = {}

        def fake_send_otp_email(user, otp_code):
            captured["email"] = user.email
            captured["otp_code"] = otp_code

        monkeypatch.setattr(service.mail_service, "send_otp_email", fake_send_otp_email)

        result = service.login(username=verified_user.username, password="Password123")

        assert result["status"] == "2fa_required"
        assert result["pending_token"]
        assert captured["email"] == verified_user.email
        assert captured["otp_code"]

    def test_verify_otp_success_clears_code(self, db, verified_user):
        """Test OTP verification clears stored code and expiry."""
        service = AuthService()
        verified_user.two_factor_enabled = True
        verified_user.generate_otp()
        _db.session.commit()

        user = service.verify_otp(verified_user.id, verified_user.otp_code)

        assert user.id == verified_user.id
        assert user.otp_code is None
        assert user.otp_expiry is None

    def test_verify_otp_rejects_invalid_code(self, db, verified_user):
        """Test invalid OTP is rejected."""
        service = AuthService()
        verified_user.two_factor_enabled = True
        verified_user.generate_otp()
        _db.session.commit()

        with pytest.raises(UnauthorizedError):
            service.verify_otp(verified_user.id, "000000")

    def test_enable_and_disable_2fa(self, db, verified_user):
        """Test enabling and disabling 2FA updates state and revokes tokens."""
        service = AuthService()
        starting_version = verified_user.token_version

        enabled = service.enable_2fa(verified_user.id, "Password123")
        assert enabled.two_factor_enabled is True
        assert enabled.token_version == starting_version + 1

        disabled = service.disable_2fa(verified_user.id, "Password123")
        assert disabled.two_factor_enabled is False
        assert disabled.token_version == starting_version + 2

    def test_login_wrong_password(self, db, verified_user):
        """Test login with wrong password."""
        service = AuthService()

        with pytest.raises(UnauthorizedError):
            service.login(username=verified_user.username, password="wrongpassword")

    def test_send_email_verification_and_verify_email(self, db, monkeypatch):
        """Test sending and confirming an email verification token."""
        service = AuthService()
        service.register(
            username="verifyme",
            email="verify@example.com",
            password="Password123",
            phone_number="7777777777",
        )

        captured = {}

        def fake_send_email_verification(user, token, recipient_email=None):
            captured["email"] = user.email
            captured["token"] = token

        monkeypatch.setattr(service.mail_service, "send_email_verification", fake_send_email_verification)

        service.send_email_verification("verify@example.com")

        assert captured["email"] == "verify@example.com"
        assert captured["token"]

        user = service.verify_email(captured["token"])
        assert user.is_verified is True


class TestPasswordStrength:
    """Test password-strength validation (defense in depth)."""

    def test_valid_password_passes(self):
        """A strong password does not raise."""
        validate_password_strength("Password123")  # should not raise

    def test_short_password_rejected(self):
        with pytest.raises(ValidationError):
            validate_password_strength("Short1")

    def test_no_uppercase_rejected(self):
        with pytest.raises(ValidationError):
            validate_password_strength("password123")

    def test_no_digit_rejected(self):
        with pytest.raises(ValidationError):
            validate_password_strength("Passwordxxx")

    def test_no_lowercase_rejected(self):
        with pytest.raises(ValidationError):
            validate_password_strength("PASSWORD123")

    def test_register_rejects_weak_password(self, db):
        """Service-layer register also enforces strength."""
        service = AuthService()
        with pytest.raises(ValidationError):
            service.register(
                username="weakpw",
                email="weakpw@test.com",
                password="password123",  # no uppercase
                phone_number="9999999999",
            )


class TestAccountLockout:
    """Test login account lockout after too many failed attempts."""

    def test_lockout_after_max_failed_attempts(self, db, verified_user):
        """Account locks after MAX_FAILED_LOGIN_ATTEMPTS wrong passwords."""
        service = AuthService()
        max_attempts = 3  # TestingConfig sets this to 3

        # Exhaust failed attempts
        for _ in range(max_attempts):
            with pytest.raises(UnauthorizedError):
                service.login(username=verified_user.username, password="wrongpw")

        # User should now be locked
        verified_user = service.user_repo.find_by_username(verified_user.username)
        assert verified_user.locked_until is not None

    def test_locked_account_rejected(self, db, verified_user):
        """Locked account returns 401 even with correct password."""
        service = AuthService()
        # Manually lock the user
        from datetime import datetime, timedelta
        service.user_repo.lock_account(
            verified_user.id,
            datetime.now(UTC) + timedelta(minutes=5),
        )

        with pytest.raises(UnauthorizedError) as exc_info:
            service.login(username=verified_user.username, password="Password123")
        assert "locked" in str(exc_info.value).lower()

    def test_successful_login_resets_failed_attempts(self, db, verified_user):
        """One failed attempt followed by success resets the counter."""
        service = AuthService()

        # One failure
        with pytest.raises(UnauthorizedError):
            service.login(username=verified_user.username, password="wrongpw")

        # Successful login resets counter
        user = service.login(username=verified_user.username, password="Password123")
        assert user.failed_attempts == 0
        assert user.locked_until is None


class TestPasswordReset:
    """Test password reset flow (forgot + reset)."""

    def test_request_password_reset_sends_email(self, db, verified_user, monkeypatch):
        """Request password reset creates a token and sends email."""
        service = AuthService()

        captured = {}

        def fake_send_reset(user, token):
            captured["token"] = token

        monkeypatch.setattr(service.mail_service, "send_password_reset_email", fake_send_reset)
        service.request_password_reset(verified_user.email)

        assert "token" in captured
        # Token should exist in the DB
        token_record = ResetTokenRepository.find_active_by_token(captured["token"])
        assert token_record is not None
        assert token_record.user_id == verified_user.id

    def test_request_password_reset_silent_for_unknown_email(self, db):
        """Forgot-password returns None silently for unknown emails."""
        service = AuthService()
        result = service.request_password_reset("nobody@example.com")
        assert result is None

    def test_reset_password_with_valid_token(self, db, verified_user, monkeypatch):
        """Reset password with a valid token changes the password."""
        service = AuthService()

        # Request reset
        captured = {}
        monkeypatch.setattr(service.mail_service, "send_password_reset_email", lambda u, t: captured.update(token=t))
        service.request_password_reset(verified_user.email)
        token = captured["token"]

        # Reset with valid token
        user = service.reset_password(token, "NewPassword456")
        assert user.check_password("NewPassword456")

    def test_reset_password_invalid_token(self, db):
        """Reset password with invalid token raises NotFoundError."""
        service = AuthService()
        with pytest.raises(NotFoundError):
            service.reset_password("invalid-token", "NewPassword456")

    def test_reset_password_weak_rejected(self, db, verified_user, monkeypatch):
        """Reset password with weak password raises ValidationError."""
        service = AuthService()
        captured = {}
        monkeypatch.setattr(service.mail_service, "send_password_reset_email", lambda u, t: captured.update(token=t))
        service.request_password_reset(verified_user.email)

        with pytest.raises(ValidationError):
            service.reset_password(captured["token"], "weak")

    def test_reset_unlocks_account(self, db, verified_user, monkeypatch):
        """Resetting password unlocks a locked account."""
        service = AuthService()

        # Lock the account
        from datetime import datetime, timedelta
        service.user_repo.lock_account(
            verified_user.id, datetime.now(UTC) + timedelta(minutes=10),
        )
        service.user_repo.increment_failed_attempts(verified_user.id)

        # Reset password
        captured = {}
        monkeypatch.setattr(service.mail_service, "send_password_reset_email", lambda u, t: captured.update(token=t))
        monkeypatch.setattr(service.mail_service, "send_password_changed_notification", lambda u: None)
        service.request_password_reset(verified_user.email)
        service.reset_password(captured["token"], "NewPassword456")

        # Account should be unlocked
        user = service.user_repo.find_by_id(verified_user.id)
        assert user.locked_until is None
        assert user.failed_attempts == 0


class TestChangePassword:
    """Test password change while logged in."""

    def test_change_password_success(self, db, verified_user, monkeypatch):
        """Change password with correct current password works."""
        service = AuthService()
        monkeypatch.setattr(service.mail_service, "send_password_changed_notification", lambda u: None)
        user = service.change_password(verified_user.id, "Password123", "NewPassword456")
        assert user.check_password("NewPassword456")

    def test_change_password_wrong_current(self, db, verified_user):
        """Change password with wrong current password raises UnauthorizedError."""
        service = AuthService()
        with pytest.raises(UnauthorizedError):
            service.change_password(verified_user.id, "WrongPassword", "NewPassword456")

    def test_change_password_same_as_current(self, db, verified_user):
        """Change password to the same value raises ValidationError."""
        service = AuthService()
        with pytest.raises(ValidationError):
            service.change_password(verified_user.id, "Password123", "Password123")

    def test_change_password_weak_new(self, db, verified_user):
        """Change password with weak new password raises ValidationError."""
        service = AuthService()
        with pytest.raises(ValidationError):
            service.change_password(verified_user.id, "Password123", "weak")


class TestAccountDeletion:
    """Test soft-delete of accounts."""

    def test_delete_account_soft_deletes(self, db, verified_user):
        """Delete account sets is_deleted=True."""
        service = AuthService()
        service.delete_account(verified_user.id)

        # Should not be findable normally
        user = service.user_repo.find_by_id(verified_user.id)
        assert user is None

        # Should be findable with include_deleted
        user = service.user_repo.find_by_id(verified_user.id, include_deleted=True)
        assert user.is_deleted is True
        assert user.deleted_at is not None

    def test_deleted_user_cannot_login(self, db, verified_user):
        """Deleted user cannot log in."""
        service = AuthService()
        service.delete_account(verified_user.id)

        with pytest.raises(UnauthorizedError):
            service.login(username=verified_user.username, password="Password123")

    def test_delete_account_stops_running_timer(self, db, verified_user):
        """Deleting an account stops any running timer first."""
        from app.features.tasks.service import TaskService
        from app.features.time_tracking.service import TimeTrackingService
        from app.features.time_tracking.models import TimeEntry

        task = TaskService().create_task(user_id=verified_user.id, title="Timed")
        timer = TimeTrackingService().start_timer(verified_user.id, [task.id])
        assert timer.running is True

        service = AuthService()
        service.delete_account(verified_user.id)

        stopped = TimeEntry.query.get(timer.id)
        assert stopped.running is False
        assert stopped.ended_at is not None
        assert stopped.duration_seconds is not None
