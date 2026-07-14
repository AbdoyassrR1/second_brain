#!/usr/bin/python3
"""Tests for auth repositories."""

import pytest
from datetime import datetime, timedelta
from app.extensions import db as _db
from app.features.auth.models import User, Role, ResetToken, VerificationToken, TokenBlocklist, UserDevice
from app.features.auth.repository import (
    UserRepository, RoleRepository, VerificationTokenRepository,
    ResetTokenRepository, TokenBlocklistRepository, UserDeviceRepository,
)


class TestRoleRepository:
    """Test RoleRepository."""

    def test_seed_default_roles(self, db):
        """Test seeding default roles."""
        result = RoleRepository.seed_default_roles()
        assert result is not None

    def test_find_by_name(self, db):
        """Test finding a role by name."""
        RoleRepository.seed_default_roles()
        role = RoleRepository.find_by_name("customer")
        assert role is not None
        assert role.name == "customer"

    def test_find_by_name_not_found(self, db):
        """Test finding a non-existent role."""
        role = RoleRepository.find_by_name("nonexistent")
        assert role is None


class TestUserRepository:
    """Test UserRepository."""

    def test_create_user(self, db):
        """Test creating a user."""
        RoleRepository.seed_default_roles()
        user = UserRepository.create(
            username="repo_test", email="repo@test.com",
            password="Password123", phone_number="1111111111",
        )
        assert user is not None
        assert user.username == "repo_test"
        assert user.email == "repo@test.com"

    def test_find_by_username(self, db, verified_user):
        """Test finding user by username."""
        user = UserRepository.find_by_username(verified_user.username)
        assert user is not None
        assert user.id == verified_user.id

    def test_find_by_email(self, db, verified_user):
        """Test finding user by email."""
        user = UserRepository.find_by_email(verified_user.email)
        assert user is not None
        assert user.username == verified_user.username

    def test_find_by_phone_number(self, db, verified_user):
        """Test finding user by phone number."""
        user = UserRepository.find_by_phone_number(verified_user.phone_number)
        assert user is not None

    def test_find_by_id(self, db, verified_user):
        """Test finding user by ID."""
        user = UserRepository.find_by_id(verified_user.id)
        assert user is not None

    def test_find_by_id_include_deleted(self, db, verified_user):
        """Test finding a soft-deleted user with include_deleted."""
        UserRepository.soft_delete(verified_user.id)

        user = UserRepository.find_by_id(verified_user.id)
        assert user is None

        user = UserRepository.find_by_id(verified_user.id, include_deleted=True)
        assert user is not None
        assert user.is_deleted is True

    def test_update_user(self, db, verified_user):
        """Test updating user fields."""
        updated = UserRepository.update(verified_user.id, first_name="Updated", last_name="Name")
        assert updated.first_name == "Updated"
        assert updated.last_name == "Name"

    def test_increment_failed_attempts(self, db, verified_user):
        """Test incrementing failed login attempts."""
        count = UserRepository.increment_failed_attempts(verified_user.id)
        assert count == 1
        count = UserRepository.increment_failed_attempts(verified_user.id)
        assert count == 2

    def test_lock_account(self, db, verified_user):
        """Test locking an account."""
        lock_until = datetime.utcnow() + timedelta(hours=1)
        UserRepository.lock_account(verified_user.id, lock_until)

        user = UserRepository.find_by_id(verified_user.id)
        assert user.locked_until is not None

    def test_reset_failed_attempts(self, db, verified_user):
        """Test resetting failed attempts."""
        UserRepository.increment_failed_attempts(verified_user.id)
        UserRepository.reset_failed_attempts(verified_user.id)

        user = UserRepository.find_by_id(verified_user.id)
        assert user.failed_attempts == 0

    def test_soft_delete(self, db, verified_user):
        """Test soft deleting a user."""
        result = UserRepository.soft_delete(verified_user.id)
        assert result is not None
        assert result.is_deleted is True
        assert result.deleted_at is not None


class TestVerificationTokenRepository:
    """Test VerificationTokenRepository."""

    def test_create_and_find(self, db, verified_user):
        """Test creating and finding a verification token."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        token = VerificationTokenRepository.create(
            verified_user.id, "test-verify-token", expiry,
        )
        assert token is not None

        found = VerificationTokenRepository.find_by_token("test-verify-token")
        assert found is not None
        assert found.user_id == verified_user.id

    def test_mark_used(self, db, verified_user):
        """Test marking a token as used."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        VerificationTokenRepository.create(verified_user.id, "test-verify-token", expiry)
        token = VerificationTokenRepository.find_by_token("test-verify-token")
        VerificationTokenRepository.mark_used(token)

        found = VerificationTokenRepository.find_by_token("test-verify-token")
        assert found.is_used is True

    def test_invalidate_user_tokens(self, db, verified_user):
        """Test invalidating all tokens for a user."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        VerificationTokenRepository.create(verified_user.id, "token-1", expiry)
        VerificationTokenRepository.create(verified_user.id, "token-2", expiry)

        VerificationTokenRepository.invalidate_user_tokens(verified_user.id)

        tokens = VerificationToken.query.filter_by(
            user_id=verified_user.id, is_used=False
        ).all()
        assert len(tokens) == 0


class TestResetTokenRepository:
    """Test ResetTokenRepository."""

    def test_create_and_find(self, db, verified_user):
        """Test creating and finding a reset token."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        token = ResetTokenRepository.create(
            verified_user.id, "test-reset-token", expiry,
        )
        assert token is not None

        found = ResetTokenRepository.find_by_token("test-reset-token")
        assert found is not None

    def test_mark_used(self, db, verified_user):
        """Test marking a reset token as used."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        ResetTokenRepository.create(verified_user.id, "test-reset-token", expiry)
        token = ResetTokenRepository.find_by_token("test-reset-token")
        ResetTokenRepository.mark_used(token)

        found = ResetTokenRepository.find_by_token("test-reset-token")
        assert found.is_used is True

    def test_invalidate_user_tokens(self, db, verified_user):
        """Test invalidating all reset tokens for a user."""
        expiry = datetime.utcnow() + timedelta(hours=1)
        ResetTokenRepository.create(verified_user.id, "reset-1", expiry)
        ResetTokenRepository.create(verified_user.id, "reset-2", expiry)

        ResetTokenRepository.invalidate_user_tokens(verified_user.id)

        tokens = ResetToken.query.filter_by(
            user_id=verified_user.id, is_used=False
        ).all()
        assert len(tokens) == 0


class TestTokenBlocklistRepository:
    """Test TokenBlocklistRepository."""

    def test_create_and_check_revoked(self, db, verified_user):
        """Test creating a blocklist entry and checking if revoked."""
        expires = datetime.utcnow() + timedelta(hours=1)
        TokenBlocklistRepository.create("test-jti", "access", verified_user.id, expires)

        assert TokenBlocklistRepository.is_revoked("test-jti") is True

    def test_not_revoked(self, db):
        """Test that a non-existent jti is not revoked."""
        assert TokenBlocklistRepository.is_revoked("nonexistent-jti") is False

    def test_create_idempotent(self, db, verified_user):
        """Test that creating the same jti twice is idempotent."""
        expires = datetime.utcnow() + timedelta(hours=1)
        first = TokenBlocklistRepository.create("dup-jti", "access", verified_user.id, expires)
        second = TokenBlocklistRepository.create("dup-jti", "access", verified_user.id, expires)
        assert first.id == second.id


class TestUserDeviceRepository:
    """Test UserDeviceRepository."""

    def test_upsert_creates(self, db, verified_user):
        """Test upsert creates a new device."""
        device = UserDeviceRepository.upsert(
            verified_user.id, device_name="Chrome", user_agent="Mozilla", ip_address="127.0.0.1"
        )
        assert device is not None
        assert device.device_name == "Chrome"

    def test_upsert_updates(self, db, verified_user):
        """Test upsert updates an existing device."""
        UserDeviceRepository.upsert(verified_user.id, device_name="Chrome", ip_address="127.0.0.1")
        updated = UserDeviceRepository.upsert(verified_user.id, device_name="Chrome", ip_address="192.168.1.1")

        assert updated.ip_address == "192.168.1.1"

    def test_find_by_user(self, db, verified_user):
        """Test finding devices by user."""
        UserDeviceRepository.upsert(verified_user.id, device_name="Device1")
        UserDeviceRepository.upsert(verified_user.id, device_name="Device2")

        p = UserDeviceRepository.find_by_user(verified_user.id)
        assert len(p.items) == 2
        assert p.total == 2

    def test_delete(self, db, verified_user):
        """Test deleting a device."""
        device = UserDeviceRepository.upsert(verified_user.id, device_name="Temp Device")
        result = UserDeviceRepository.delete(device.id, verified_user.id)
        assert result is True

        p = UserDeviceRepository.find_by_user(verified_user.id)
        assert len(p.items) == 0
        assert p.total == 0

    def test_delete_not_found(self, db, verified_user):
        """Test deleting a non-existent device."""
        result = UserDeviceRepository.delete("nonexistent", verified_user.id)
        assert result is False

