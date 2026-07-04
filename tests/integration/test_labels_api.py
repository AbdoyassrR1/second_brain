#!/usr/bin/python3
"""Tests for label endpoints."""

import pytest
from app.extensions import db as _db
from app.features.auth.models import VerificationToken


def _register_and_verify_user(client, username, email, password, phone):
    """Helper to register and verify a user, returning auth headers."""
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password, "phone_number": phone},
    )
    token_record = VerificationToken.query.filter(VerificationToken.is_used.is_(False)).first()
    if token_record:
        client.post("/api/v1/auth/verify-email", json={"token": token_record.token})
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.get_json()}"
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

#!/usr/bin/python3
"""Tests for label endpoints."""

import pytest


class TestLabelCreate:
    """Test label creation endpoint."""

    def test_create_label_success(self, client, db, auth_headers):
        """Test successful label creation."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/labels",
            headers=headers,
            json={"name": "urgent", "color": "#FF0000"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["label"]["name"] == "urgent"
        assert data["label"]["color"] == "#FF0000"

    def test_create_label_unauthorized(self, client, db):
        """Test label creation without authentication."""
        response = client.post(
            "/api/v1/labels",
            json={"name": "urgent"},
        )
        assert response.status_code == 401

    def test_create_label_missing_name(self, client, db, auth_headers):
        """Test label creation without required name."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/labels",
            headers=headers,
            json={"color": "#FF0000"},
        )
        assert response.status_code == 400

    def test_create_label_empty_name(self, client, db, auth_headers):
        """Test label creation with empty name."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/labels",
            headers=headers,
            json={"name": ""},
        )
        assert response.status_code == 400

    def test_create_label_non_json(self, client, db, auth_headers):
        """Test label creation with non-JSON content type."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/labels",
            headers=headers,
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code == 415


class TestLabelList:
    """Test label listing endpoint."""

    def test_list_labels_empty(self, client, db, auth_headers):
        """Test listing labels when none exist."""
        headers, _ = auth_headers
        response = client.get("/api/v1/labels", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["count"] == 0

    def test_list_labels_with_data(self, client, db, auth_headers):
        """Test listing labels after creating some."""
        headers, _ = auth_headers
        client.post("/api/v1/labels", headers=headers, json={"name": "urgent"})
        client.post("/api/v1/labels", headers=headers, json={"name": "bug"})
        client.post("/api/v1/labels", headers=headers, json={"name": "feature"})

        response = client.get("/api/v1/labels", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 3
        assert len(data["labels"]) == 3

    def test_list_labels_unauthorized(self, client, db):
        """Test listing labels without authentication."""
        response = client.get("/api/v1/labels")
        assert response.status_code == 401

    def test_list_labels_user_isolation(self, client, db, auth_headers):
        """Test labels are isolated between users."""
        headers1, _ = auth_headers
        client.post("/api/v1/labels", headers=headers1, json={"name": "user1-label"})

        headers2 = _register_and_verify_user(
            client, "user2", "user2@example.com", "Password123", "2222222222"
        )
        response = client.get("/api/v1/labels", headers=headers2)
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 0


class TestLabelDelete:
    """Test label deletion endpoint."""

    def test_delete_label_success(self, client, db, auth_headers):
        """Test successful label deletion."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/labels", headers=headers, json={"name": "temporary"}
        )
        label_id = create_resp.get_json()["label"]["id"]

        response = client.delete(f"/api/v1/labels/{label_id}", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        list_resp = client.get("/api/v1/labels", headers=headers)
        assert list_resp.get_json()["count"] == 0

    def test_delete_label_unauthorized(self, client, db, auth_headers):
        """Test label deletion without authentication."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/labels", headers=headers, json={"name": "temp"}
        )
        label_id = create_resp.get_json()["label"]["id"]

        response = client.delete(f"/api/v1/labels/{label_id}")
        assert response.status_code == 401

    def test_delete_label_not_found(self, client, db, auth_headers):
        """Test deleting a non-existent label."""
        headers, _ = auth_headers
        response = client.delete("/api/v1/labels/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_delete_label_forbidden(self, client, db, auth_headers):
        """Test deleting another user's label."""
        headers1, _ = auth_headers
        create_resp = client.post(
            "/api/v1/labels", headers=headers1, json={"name": "others-label"}
        )
        label_id = create_resp.get_json()["label"]["id"]

        headers2 = _register_and_verify_user(
            client, "otheruser", "other@example.com", "Password123", "3333333333"
        )
        response = client.delete(f"/api/v1/labels/{label_id}", headers=headers2)
        assert response.status_code == 403
