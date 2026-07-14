#!/usr/bin/python3
"""Tests for project endpoints."""

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
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.get_json()}"
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

#!/usr/bin/python3
"""Tests for project endpoints."""

import pytest


class TestProjectCreate:
    """Test project creation endpoint."""

    def test_create_project_success(self, client, db, auth_headers):
        """Test successful project creation."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/projects",
            headers=headers,
            json={"name": "My Project", "description": "A test project", "color": "#00FF00"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["project"]["name"] == "My Project"
        assert data["project"]["description"] == "A test project"
        assert data["project"]["color"] == "#00FF00"

    def test_create_project_unauthorized(self, client, db):
        """Test project creation without authentication."""
        response = client.post("/api/v1/projects", json={"name": "Test"})
        assert response.status_code == 401

    def test_create_project_missing_name(self, client, db, auth_headers):
        """Test project creation without required name."""
        headers, _ = auth_headers
        response = client.post("/api/v1/projects", headers=headers, json={"description": "No name"})
        assert response.status_code == 400

    def test_create_project_empty_name(self, client, db, auth_headers):
        """Test project creation with empty name."""
        headers, _ = auth_headers
        response = client.post("/api/v1/projects", headers=headers, json={"name": ""})
        assert response.status_code == 400

    def test_create_project_non_json(self, client, db, auth_headers):
        """Test project creation with non-JSON content type."""
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/projects",
            headers=headers,
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code == 415


class TestProjectList:
    """Test project listing endpoint."""

    def test_list_projects_empty(self, client, db, auth_headers):
        """Test listing projects when none exist."""
        headers, _ = auth_headers
        response = client.get("/api/v1/projects", headers=headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_projects_with_data(self, client, db, auth_headers):
        """Test listing projects after creating some."""
        headers, _ = auth_headers
        client.post("/api/v1/projects", headers=headers, json={"name": "Work"})
        client.post("/api/v1/projects", headers=headers, json={"name": "Personal"})

        response = client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_projects_unauthorized(self, client, db):
        """Test listing projects without authentication."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


class TestProjectGet:
    """Test single project retrieval endpoint."""

    def test_get_project_success(self, client, db, auth_headers):
        """Test getting a project by ID."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Specific"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        response = client.get(f"/api/v1/projects/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["project"]["id"] == project_id
        assert data["project"]["name"] == "Specific"

    def test_get_project_not_found(self, client, db, auth_headers):
        """Test getting a non-existent project."""
        headers, _ = auth_headers
        response = client.get("/api/v1/projects/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_get_project_forbidden(self, client, db, auth_headers):
        """Test getting another user's project."""
        headers1, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers1, json={"name": "Private"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        headers2 = _register_and_verify_user(
            client, "otheruser", "other@test.com", "Password123", "4444444444"
        )
        response = client.get(f"/api/v1/projects/{project_id}", headers=headers2)
        assert response.status_code == 403


class TestProjectUpdate:
    """Test project update endpoint."""

    def test_update_project_success(self, client, db, auth_headers):
        """Test successful project update."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Old Name"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        response = client.patch(
            f"/api/v1/projects/{project_id}",
            headers=headers,
            json={"name": "New Name", "description": "Updated"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["project"]["name"] == "New Name"
        assert data["project"]["description"] == "Updated"

    def test_update_project_unauthorized(self, client, db, auth_headers):
        """Test updating a project without authentication."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Test"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        response = client.patch(
            f"/api/v1/projects/{project_id}", json={"name": "Hacked"}
        )
        assert response.status_code == 401

    def test_update_project_not_found(self, client, db, auth_headers):
        """Test updating a non-existent project."""
        headers, _ = auth_headers
        response = client.patch(
            "/api/v1/projects/nonexistent", headers=headers, json={"name": "New"}
        )
        assert response.status_code == 404

    def test_update_project_forbidden(self, client, db, auth_headers):
        """Test updating another user's project."""
        headers1, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers1, json={"name": "Not Yours"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        headers2 = _register_and_verify_user(
            client, "user3", "user3@test.com", "Password123", "5555555555"
        )
        response = client.patch(
            f"/api/v1/projects/{project_id}", headers=headers2, json={"name": "Hacked"}
        )
        assert response.status_code == 403


class TestProjectDelete:
    """Test project deletion endpoint."""

    def test_delete_project_success(self, client, db, auth_headers):
        """Test successful project deletion."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Temp"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        response = client.delete(f"/api/v1/projects/{project_id}", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"

        # Verify it's gone
        get_resp = client.get(f"/api/v1/projects/{project_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_delete_project_unauthorized(self, client, db, auth_headers):
        """Test deleting a project without authentication."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers, json={"name": "Temp"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        response = client.delete(f"/api/v1/projects/{project_id}")
        assert response.status_code == 401

    def test_delete_project_not_found(self, client, db, auth_headers):
        """Test deleting a non-existent project."""
        headers, _ = auth_headers
        response = client.delete("/api/v1/projects/nonexistent", headers=headers)
        assert response.status_code == 404

    def test_delete_project_forbidden(self, client, db, auth_headers):
        """Test deleting another user's project."""
        headers1, _ = auth_headers
        create_resp = client.post(
            "/api/v1/projects", headers=headers1, json={"name": "Not Yours"}
        )
        project_id = create_resp.get_json()["project"]["id"]

        headers2 = _register_and_verify_user(
            client, "user4", "user4@test.com", "Password123", "6666666666"
        )
        response = client.delete(f"/api/v1/projects/{project_id}", headers=headers2)
        assert response.status_code == 403
