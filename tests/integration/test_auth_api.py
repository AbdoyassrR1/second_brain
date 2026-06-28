#!/usr/bin/python3
"""Tests for authentication endpoints."""

import pytest


class TestAuthRegister:
    """Test user registration endpoint."""

    def test_register_success(self, client, db):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "Password123",
                "phone_number": "9876543210",
            },
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert "user" in data
        assert data["user"]["username"] == "newuser"

    def test_register_duplicate_username(self, client, db, auth_headers):
        """Test registration with duplicate username."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",  # Already exists from auth_headers fixture
                "email": "another@example.com",
                "password": "Password123",
                "phone_number": "1111111111",
            },
        )

        assert response.status_code == 409
        data = response.get_json()
        assert data["status"] == "error"

    def test_register_invalid_password(self, client, db):
        """Test registration with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "user",
                "email": "user@example.com",
                "password": "short",  # Too short
                "phone_number": "5555555555",
            },
        )

        assert response.status_code == 400

    def test_register_password_no_uppercase(self, client, db):
        """Test registration with password missing uppercase."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "noupp",
                "email": "noupp@example.com",
                "password": "password123",  # No uppercase
                "phone_number": "5555555556",
            },
        )

        assert response.status_code == 400

    def test_register_password_no_digit(self, client, db):
        """Test registration with password missing digit."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "nodigit",
                "email": "nodigit@example.com",
                "password": "Passwordxxx",  # No digit
                "phone_number": "5555555557",
            },
        )

        assert response.status_code == 400


class TestEmailVerification:
    """Test email verification endpoints."""

    def test_send_email_verification_success(self, client, db):
        """Test sending a verification email."""
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "verifyuser",
                "email": "verifyuser@example.com",
                "password": "Password123",
                "phone_number": "4444444444",
            },
        )

        response = client.post(
            "/api/v1/auth/send-email-verification",
            json={"email": "verifyuser@example.com"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

    def test_verify_email_with_invalid_token(self, client, db):
        """Test verifying an email with an invalid token."""
        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token"},
        )

        assert response.status_code == 404


class TestAuthLogin:
    """Test user login endpoint."""

    def test_login_success(self, client, db, auth_headers):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password123"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_invalid_credentials(self, client, db, auth_headers):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        """Test login with nonexistent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "Password123"},
        )

        assert response.status_code == 401

    def test_login_unverified_user_rejected(self, client, db):
        """Test that an unverified user cannot log in."""
        from app.extensions import db as _db
        from app.features.auth.models import User
        from app.features.auth.repository import RoleRepository

        role = RoleRepository.find_by_name("customer")
        user = User(
            username="unverified",
            email="unverified@test.com",
            phone_number="1231231234",
            role_id=role.id,
            is_verified=False,
        )
        user.set_password("Password123")
        _db.session.add(user)
        _db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "unverified@test.com", "password": "Password123"},
        )

        assert response.status_code == 401

    def test_login_with_2fa_returns_pending_token(self, client, db, verified_user, monkeypatch):
        """Test login returns a pending token when 2FA is enabled."""
        from app.extensions import db as _db

        verified_user.two_factor_enabled = True
        _db.session.commit()

        monkeypatch.setattr(
            "app.features.auth.routes.auth_service.mail_service.send_otp_email",
            lambda user, otp_code: None,
        )

        response = client.post(
            "/api/v1/auth/login",
            json={"username": verified_user.username, "password": "Password123"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "2fa_required"
        assert data["pending_token"]

    def test_verify_otp_flow_issues_tokens(self, client, db, verified_user, monkeypatch):
        """Test the full 2FA login flow returns normal tokens after OTP verification."""
        from app.extensions import db as _db
        from app.features.auth.models import User

        verified_user.two_factor_enabled = True
        _db.session.commit()

        monkeypatch.setattr(
            "app.features.auth.routes.auth_service.mail_service.send_otp_email",
            lambda user, otp_code: None,
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": verified_user.email, "password": "Password123"},
        )
        assert login_response.status_code == 200
        login_data = login_response.get_json()
        assert login_data["status"] == "2fa_required"

        user = _db.session.query(User).filter_by(id=verified_user.id).first()
        otp_code = user.otp_code

        response = client.post(
            "/api/v1/auth/verify-otp",
            json={"pending_token": login_data["pending_token"], "otp_code": otp_code},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_pending_token_is_rejected_on_protected_route(self, client, db, verified_user, monkeypatch):
        """Test a pending 2FA token cannot access normal protected routes."""
        from app.extensions import db as _db

        verified_user.two_factor_enabled = True
        _db.session.commit()

        monkeypatch.setattr(
            "app.features.auth.routes.auth_service.mail_service.send_otp_email",
            lambda user, otp_code: None,
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={"email": verified_user.email, "password": "Password123"},
        )
        pending_token = login_response.get_json()["pending_token"]

        response = client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {pending_token}"},
        )

        assert response.status_code == 401


class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_profile_success(self, client, db, auth_headers):
        """Test getting current user profile."""
        headers, user_id = auth_headers
        response = client.get("/api/v1/me", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["user"]["username"] == "testuser"

    def test_get_profile_unauthorized(self, client, db):
        """Test getting profile without authentication."""
        response = client.get("/api/v1/me")

        assert response.status_code == 401


class TestRefresh:
    """Test token refresh endpoint."""

    def test_refresh_success(self, client, db, auth_headers):
        """Test refreshing tokens with a valid refresh token."""
        # Get refresh token from login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password123"},
        )
        refresh_token = response.get_json()["refresh_token"]

        # Use the refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_access_token_rejected(self, client, db, auth_headers):
        """Test that an access token cannot be used to refresh."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/auth/refresh",
            headers=headers,
        )

        assert response.status_code == 401

    def test_refresh_revokes_old_token(self, client, db, auth_headers):
        """Test that the old refresh token is revoked after rotation."""
        # Get initial tokens
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Password123"},
        )
        old_refresh = response.get_json()["refresh_token"]

        # Rotate
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_refresh}"},
        )
        assert response.status_code == 200

        # Old refresh token should now be rejected
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_refresh}"},
        )
        assert response.status_code == 401


class TestLogout:
    """Test logout endpoints."""

    def test_logout_success(self, client, db, auth_headers):
        """Test logout revokes the current token."""
        headers, _ = auth_headers
        response = client.post("/api/v1/auth/logout", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["status"] == "success"

    def test_logout_revokes_token(self, client, db, auth_headers):
        """Test that the access token is rejected after logout."""
        headers, _ = auth_headers
        client.post("/api/v1/auth/logout", headers=headers)

        # The revoked token should no longer work
        response = client.get("/api/v1/me", headers=headers)
        assert response.status_code == 401

    def test_logout_all(self, client, db, auth_headers):
        """Test logout-all endpoint returns success."""
        headers, _ = auth_headers
        response = client.post("/api/v1/auth/logout-all", headers=headers)
        assert response.status_code == 200


class TestPasswordReset:
    """Test forgot-password and reset-password endpoints."""

    def test_forgot_password_always_200(self, client, db):
        """Forgot-password returns 200 even for unknown emails (no enumeration)."""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nobody@example.com"},
        )
        assert response.status_code == 200

    def test_forgot_password_creates_reset_token(self, client, db, verified_user):
        """Forgot-password creates a usable reset token for a real user."""
        from app.features.auth.repository import ResetTokenRepository

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": verified_user.email},
        )
        assert response.status_code == 200

        # A reset token should exist for this user
        # tokens = ResetTokenRepository.find_active_by_token(
            # We need to find it — grab from the query
        # )
        # Query all active tokens for the user
        from app.extensions import db as _db
        from app.features.auth.models import ResetToken
        token = _db.session.query(ResetToken).filter_by(
            user_id=verified_user.id, is_used=False
        ).first()
        assert token is not None

    def test_reset_password_flow(self, client, db, verified_user):
        """Full flow: forgot → reset → login with new password."""
        from app.features.auth.repository import ResetTokenRepository
        from app.extensions import db as _db
        from app.features.auth.models import ResetToken

        # Step 1: Request reset
        client.post(
            "/api/v1/auth/forgot-password",
            json={"email": verified_user.email},
        )

        # Step 2: Grab the token from DB
        token_record = _db.session.query(ResetToken).filter_by(
            user_id=verified_user.id, is_used=False
        ).first()
        assert token_record is not None

        # Step 3: Reset password
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": token_record.token, "new_password": "NewPassword456"},
        )
        assert response.status_code == 200
        assert response.get_json()["status"] == "success"

        # Step 4: Login with new password
        response = client.post(
            "/api/v1/auth/login",
            json={"email": verified_user.email, "password": "NewPassword456"},
        )
        assert response.status_code == 200

    def test_reset_password_invalid_token(self, client, db):
        """Reset with an invalid token returns 404."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid-token", "new_password": "NewPassword456"},
        )
        assert response.status_code == 404


class TestChangePassword:
    """Test change-password endpoint."""

    def test_change_password_success(self, client, db, auth_headers, verified_user):
        """Change password with correct current password."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "Password123", "new_password": "NewPassword456"},
        )
        assert response.status_code == 200

        # Can login with new password (need new token since change-password
        # revokes all tokens)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": verified_user.email, "password": "NewPassword456"},
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client, db, auth_headers):
        """Change password with wrong current password returns 401."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "WrongPassword", "new_password": "NewPassword456"},
        )
        assert response.status_code == 401

    def test_change_password_weak_new(self, client, db, auth_headers):
        """Change password with weak new password returns 400."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/auth/change-password",
            headers=headers,
            json={"current_password": "Password123", "new_password": "weak"},
        )
        assert response.status_code == 400


class TestAccountManagement:
    """Test /me endpoints (GET, PATCH, DELETE)."""

    def test_get_me(self, client, db, auth_headers):
        """Test GET /me returns profile."""
        headers, _ = auth_headers
        response = client.get("/api/v1/me", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["user"]["username"] == "testuser"

    def test_patch_me_update_username(self, client, db, auth_headers):
        """Test PATCH /me updates username."""
        headers, _ = auth_headers
        response = client.patch(
            "/api/v1/me",
            headers=headers,
            json={"username": "newusername"},
        )
        assert response.status_code == 200
        assert response.get_json()["user"]["username"] == "newusername"

    def test_patch_me_rejects_email_update(self, client, db, auth_headers):
        """Test PATCH /me rejects direct email updates."""
        headers, _ = auth_headers

        response = client.patch(
            "/api/v1/me",
            headers=headers,
            json={"email": "other@example.com"},
        )
        assert response.status_code == 400

    def test_change_email_flow(self, client, db, auth_headers, verified_user):
        """Test POST /me/change-email keeps the old email until verified."""
        headers, _ = auth_headers

        response = client.post(
            "/api/v1/me/change-email",
            headers=headers,
            json={
                "current_password": "Password123",
                "new_email": "pending-change@example.com",
            },
        )
        assert response.status_code == 200

        from app.extensions import db as _db
        from app.features.auth.models import User, VerificationToken

        user = _db.session.query(User).filter_by(id=verified_user.id).first()
        assert user.email == "test@example.com"
        assert user.pending_email == "pending-change@example.com"
        assert user.is_verified is True

        token = _db.session.query(VerificationToken).filter_by(
            user_id=verified_user.id, is_used=False
        ).first()
        assert token is not None

        response = client.post(
            "/api/v1/auth/verify-email",
            json={"token": token.token},
        )
        assert response.status_code == 200

        _db.session.refresh(user)
        assert user.email == "pending-change@example.com"
        assert user.pending_email is None
        assert user.is_verified is True

        response = client.post(
            "/api/v1/auth/login",
            json={"email": "pending-change@example.com", "password": "Password123"},
        )
        assert response.status_code == 200

    def test_delete_me(self, client, db, auth_headers, verified_user):
        """Test DELETE /me soft-deletes the account."""
        headers, _ = auth_headers
        response = client.delete("/api/v1/me", headers=headers)
        assert response.status_code == 200

        # Cannot log in after deletion
        response = client.post(
            "/api/v1/auth/login",
            json={"email": verified_user.email, "password": "Password123"},
        )
        assert response.status_code == 401

    def test_delete_me_revokes_tokens(self, client, db, auth_headers):
        """Test that DELETE /me immediately invalidates the token."""
        headers, _ = auth_headers
        client.delete("/api/v1/me", headers=headers)

        # Token should be rejected
        response = client.get("/api/v1/me", headers=headers)
        assert response.status_code == 401


class TestLockout:
    """Test account lockout at the API level."""

    def test_lockout_after_repeated_failures(self, client, db, verified_user):
        """Account locks after 3 wrong password attempts (TestingConfig)."""
        for _ in range(3):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": verified_user.username, "password": "wrongpw"},
            )
            assert response.status_code == 401

        # 4th attempt (even with correct password) should be rejected
        response = client.post(
            "/api/v1/auth/login",
            json={"username": verified_user.username, "password": "Password123"},
        )
        assert response.status_code == 401
        assert "locked" in response.get_json()["message"].lower()


class TestDevices:
    """Test device tracking endpoint."""

    def test_list_devices_after_login(self, client, db, auth_headers):
        """Test GET /me/devices shows devices after login."""
        headers, _ = auth_headers
        response = client.get("/api/v1/me/devices", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "devices" in data
        assert data["count"] >= 1
