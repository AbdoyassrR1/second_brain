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
                "password": "password123",
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
                "password": "password123",
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


class TestEmailVerification:
    """Test email verification endpoints."""

    def test_send_email_verification_success(self, client, db):
        """Test sending a verification email."""
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "verifyuser",
                "email": "verifyuser@example.com",
                "password": "password123",
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
            json={"username": "testuser", "password": "password123"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "access_token" in data

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
            json={"username": "nonexistent", "password": "password123"},
        )
        
        assert response.status_code == 401


class TestUserProfile:
    """Test user profile endpoints."""

    def test_get_profile_success(self, client, db, auth_headers):
        """Test getting current user profile."""
        headers, user_id = auth_headers
        response = client.get("/api/v1/auth/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["user"]["username"] == "testuser"

    def test_get_profile_unauthorized(self, client, db):
        """Test getting profile without authentication."""
        response = client.get("/api/v1/auth/profile")
        
        assert response.status_code == 401
