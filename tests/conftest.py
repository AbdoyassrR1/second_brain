#!/usr/bin/python3
"""Shared test configuration and fixtures."""

from datetime import datetime

import pytest
from app import create_app
from app.extensions import db as _db
from app.features.auth.models import User
from app.features.auth.repository import RoleRepository


@pytest.fixture(scope="session")
def app():
    """Create application for test session."""
    app = create_app("testing")
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Test client for making requests."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Create database for test."""
    with app.app_context():
        _db.create_all()
        RoleRepository.seed_default_roles()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def runner(app):
    """CLI runner for commands."""
    return app.test_cli_runner()


@pytest.fixture
def verified_user(db):
    """Create a verified user for login-dependent tests."""
    role = RoleRepository.find_by_name("customer")
    assert role is not None

    user = User(
        username="testuser",
        email="test@example.com",
        phone_number="1234567890",
        role_id=role.id,
        is_verified=True,
        verified_at=datetime.utcnow(),
        is_active=True,
    )
    user.set_password("Password123")
    _db.session.add(user)
    _db.session.commit()
    return user


@pytest.fixture
def auth_headers(client, verified_user):
    """Return authenticated headers for a verified test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": verified_user.email,
            "password": "Password123",
        },
    )
    
    assert response.status_code == 200
    data = response.get_json()
    access_token = data["access_token"]
    
    return {"Authorization": f"Bearer {access_token}"}, data["user"]["id"]


@pytest.fixture
def test_user_id(auth_headers):
    """Extract user ID from auth headers fixture."""
    return auth_headers[1]
