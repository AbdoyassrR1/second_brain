#!/usr/bin/python3
"""Tests for auth service business logic."""

import pytest
from app.features.auth.service import AuthService
from app.shared.exceptions import ValidationError, ConflictError, UnauthorizedError


class TestAuthService:
    """Test auth service."""

    def test_register_user(self, db):
        """Test user registration through service."""
        service = AuthService()
        user = service.register(
            username="servicetest",
            email="service@test.com",
            password="password123",
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
            password="password123",
            phone_number="1111111111",
        )
        
        with pytest.raises(ConflictError):
            service.register(
                username="existing",
                email="second@test.com",
                password="password123",
                phone_number="2222222222",
            )

    def test_login_success(self, db, verified_user):
        """Test successful login."""
        service = AuthService()
        user = service.login(username=verified_user.username, password="password123")
        assert user.username == verified_user.username

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
            password="password123",
phone_number="7777777777",                                                                                                                                                                                                                                                                                                                                                                                                                                              
        )

        captured = {}

        def fake_send_email_verification(user, token):
            captured["email"] = user.email
            captured["token"] = token                                                                                                                                                                                               

        monkeypatch.setattr(service.mail_service, "send_email_verification", fake_send_email_verification)

        service.send_email_verification("verify@example.com")

        assert captured["email"] == "verify@example.com"
        assert captured["token"]

        user = service.verify_email(captured["token"])
        assert user.is_verified is True

