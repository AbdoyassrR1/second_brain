#!/usr/bin/python3
"""Tests for task endpoints."""

import pytest


class TestTaskCreate:
    """Test task creation endpoint."""

    def test_create_task_success(self, client, db, auth_headers):
        """Test successful task creation."""
        headers, user_id = auth_headers
        response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={
                "title": "Test Task",
                "description": "A test task",
                "due_date": "2026-12-31",
                "priority": "high",
            },
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["task"]["title"] == "Test Task"
        assert data["task"]["user_id"] == user_id

    def test_create_task_unauthorized(self, client, db):
        """Test task creation without authentication."""
        response = client.post(
            "/api/v1/tasks",
            json={
                "title": "Test Task",
                "description": "A test task",
            },
        )
        
        assert response.status_code == 401


class TestTaskList:
    """Test task listing endpoint."""

    def test_list_tasks_empty(self, client, db, auth_headers):
        """Test listing tasks when none exist."""
        headers, user_id = auth_headers
        response = client.get("/api/v1/tasks", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["count"] == 0

    def test_list_tasks_with_data(self, client, db, auth_headers):
        """Test listing tasks after creating some."""
        headers, user_id = auth_headers
        
        # Create two tasks
        for i in range(2):
            client.post(
                "/api/v1/tasks",
                headers=headers,
                json={"title": f"Task {i}", "priority": "low"},
            )
        
        response = client.get("/api/v1/tasks", headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2


class TestTaskUpdate:
    """Test task update endpoint."""

    def test_update_task_success(self, client, db, auth_headers):
        """Test successful task update."""
        headers, user_id = auth_headers
        
        # Create task
        create_response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Original Title"},
        )
        task_id = create_response.get_json()["task"]["id"]
        
        # Update task
        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
            json={"title": "Updated Title"},
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["title"] == "Updated Title"


class TestTaskDelete:
    """Test task deletion endpoint."""

    def test_delete_task_success(self, client, db, auth_headers):
        """Test successful task deletion."""
        headers, user_id = auth_headers
        
        # Create task
        create_response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Task to Delete"},
        )
        task_id = create_response.get_json()["task"]["id"]
        
        # Delete task
        response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
        )
        
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
        )
        assert get_response.status_code == 404
