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
        assert data["total"] == 0

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
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_list_tasks_pagination(self, client, db, auth_headers):
        """Test paginated task listing."""
        headers, user_id = auth_headers
        
        # Create 5 tasks
        for i in range(5):
            client.post(
                "/api/v1/tasks",
                headers=headers,
                json={"title": f"Task {i}", "priority": "low"},
            )
        
        response = client.get("/api/v1/tasks?page=1&page_size=2", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total"] == 5
        assert data["pages"] == 3
        assert len(data["items"]) == 2

    def test_list_tasks_sorting(self, client, db, auth_headers):
        """Test sorted task listing."""
        headers, user_id = auth_headers
        
        client.post("/api/v1/tasks", headers=headers, json={"title": "A Task", "priority": "low"})
        client.post("/api/v1/tasks", headers=headers, json={"title": "B Task", "priority": "high"})
        
        response = client.get("/api/v1/tasks?sort=title", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["items"][0]["title"] == "A Task"

    def test_list_tasks_search(self, client, db, auth_headers):
        """Test searching tasks."""
        headers, user_id = auth_headers
        
        client.post("/api/v1/tasks", headers=headers, json={"title": "Shopping List", "description": "Buy groceries"})
        client.post("/api/v1/tasks", headers=headers, json={"title": "Work Task", "description": "Finish project"})
        
        response = client.get("/api/v1/tasks?q=shopping", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Shopping List"


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
        """Test successful task soft deletion."""
        headers, user_id = auth_headers
        
        # Create task
        create_response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Task to Delete"},
        )
        task_id = create_response.get_json()["task"]["id"]
        
        # Delete task (soft delete)
        response = client.delete(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
        )
        
        assert response.status_code == 200
        
        # Verify it's soft-deleted (returns 404 for normal get)
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
        )
        assert get_response.status_code == 404

    def test_restore_task_success(self, client, db, auth_headers):
        """Test restoring a soft-deleted task."""
        headers, user_id = auth_headers
        
        # Create and soft-delete a task
        create_response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Task to Restore"},
        )
        task_id = create_response.get_json()["task"]["id"]
        
        client.delete(f"/api/v1/tasks/{task_id}", headers=headers)
        
        # Restore it
        response = client.post(
            f"/api/v1/tasks/{task_id}/restore",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["is_deleted"] is False
        
        # Verify it's accessible again
        get_response = client.get(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
        )
        assert get_response.status_code == 200


class TestTaskArchive:
    """Test task archive endpoint."""

    def test_archive_and_restore_task(self, client, db, auth_headers):
        """Test archiving and restoring a task."""
        headers, user_id = auth_headers
        
        # Create task
        create_response = client.post(
            "/api/v1/tasks",
            headers=headers,
            json={"title": "Task to Archive"},
        )
        task_id = create_response.get_json()["task"]["id"]
        
        # Archive it
        response = client.post(
            f"/api/v1/tasks/{task_id}/archive",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["is_archived"] is True
        
        # Restore from archive
        response = client.post(
            f"/api/v1/tasks/{task_id}/restore-archive",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["is_archived"] is False


class TestTaskStatistics:
    """Test task statistics endpoint."""

    def test_get_statistics(self, client, db, auth_headers):
        """Test getting task statistics."""
        headers, user_id = auth_headers
        
        response = client.get("/api/v1/tasks/statistics", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "total_tasks" in data["statistics"]
        assert "completion_rate" in data["statistics"]