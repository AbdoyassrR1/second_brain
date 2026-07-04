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


class TestTaskUpdate:
    """Test task update endpoint."""

    def test_update_task_success(self, client, db, auth_headers):
        """Test successful task update via PATCH."""
        headers, user_id = auth_headers

        create_resp = client.post(
            "/api/v1/tasks", headers=headers,
            json={"title": "Original Title", "priority": "low"},
        )
        task_id = create_resp.get_json()["task"]["id"]

        response = client.patch(
            f"/api/v1/tasks/{task_id}",
            headers=headers,
            json={"title": "Updated Title", "priority": "high"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["title"] == "Updated Title"
        assert data["task"]["priority"] == "high"

    def test_update_task_unauthorized(self, client, db, auth_headers):
        """Test updating a task without authentication."""
        headers, _ = auth_headers
        create_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Test"}
        )
        task_id = create_resp.get_json()["task"]["id"]

        response = client.patch(
            f"/api/v1/tasks/{task_id}", json={"title": "Hacked"}
        )
        assert response.status_code == 401

    def test_update_task_not_found(self, client, db, auth_headers):
        """Test updating a non-existent task."""
        headers, _ = auth_headers
        response = client.patch(
            "/api/v1/tasks/nonexistent", headers=headers, json={"title": "New"}
        )
        assert response.status_code == 404


class TestTaskAdvancedFilters:
    """Test advanced filtering on task listing."""

    def test_filter_by_priority(self, client, db, auth_headers):
        """Test filtering tasks by priority."""
        headers, _ = auth_headers
        client.post("/api/v1/tasks", headers=headers, json={"title": "High Priority", "priority": "high"})
        client.post("/api/v1/tasks", headers=headers, json={"title": "Low Priority", "priority": "low"})

        response = client.get("/api/v1/tasks?priority=high", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["priority"] == "high"

    def test_filter_by_status(self, client, db, auth_headers):
        """Test filtering tasks by status."""
        headers, _ = auth_headers
        client.post("/api/v1/tasks", headers=headers, json={"title": "Todo Task", "status": "todo"})
        client.post("/api/v1/tasks", headers=headers, json={"title": "Done Task", "status": "completed"})

        response = client.get("/api/v1/tasks?status=completed", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    def test_search_by_query(self, client, db, auth_headers):
        """Test searching tasks by query."""
        headers, _ = auth_headers
        client.post("/api/v1/tasks", headers=headers, json={"title": "Find Me Please"})
        client.post("/api/v1/tasks", headers=headers, json={"title": "Other Task"})

        response = client.get("/api/v1/tasks?q=Find", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1


class TestTaskRestore:
    """Test task restore endpoint."""

    def test_restore_soft_deleted_task(self, client, db, auth_headers):
        """Test restoring a soft-deleted task."""
        headers, _ = auth_headers

        create_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task to Restore"}
        )
        task_id = create_resp.get_json()["task"]["id"]

        # Soft delete
        client.delete(f"/api/v1/tasks/{task_id}", headers=headers)

        # Restore
        response = client.post(f"/api/v1/tasks/{task_id}/restore", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["task"]["is_deleted"] is False

        # Verify accessible again
        get_resp = client.get(f"/api/v1/tasks/{task_id}", headers=headers)
        assert get_resp.status_code == 200


class TestTaskSubtasks:
    """Test subtask endpoints."""

    def test_create_and_list_subtasks(self, client, db, auth_headers):
        """Test creating a subtask and listing subtasks."""
        headers, _ = auth_headers

        parent_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Parent Task"}
        )
        parent_id = parent_resp.get_json()["task"]["id"]

        client.post(
            "/api/v1/tasks", headers=headers,
            json={"title": "Subtask", "parent_task_id": parent_id},
        )

        response = client.get(f"/api/v1/tasks/{parent_id}/subtasks", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["subtasks"]) == 1
        assert data["subtasks"][0]["title"] == "Subtask"


class TestTaskBulkOperations:
    """Test bulk task operations."""

    def _create_tasks(self, client, headers, count=3):
        """Helper to create multiple tasks."""
        ids = []
        for i in range(count):
            resp = client.post(
                "/api/v1/tasks", headers=headers, json={"title": f"Bulk Task {i}"}
            )
            ids.append(resp.get_json()["task"]["id"])
        return ids

    def test_bulk_delete(self, client, db, auth_headers):
        """Test bulk soft delete."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        response = client.delete(
            "/api/v1/tasks/bulk",
            headers=headers,
            json={"task_ids": task_ids},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data["status"]

        list_resp = client.get("/api/v1/tasks", headers=headers)
        assert list_resp.get_json()["total"] == 0

    def test_bulk_complete(self, client, db, auth_headers):
        """Test bulk complete tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        response = client.post(
            "/api/v1/tasks/bulk/complete",
            headers=headers,
            json={"task_ids": task_ids},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data["status"]

    def test_bulk_archive(self, client, db, auth_headers):
        """Test bulk archive tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        response = client.post(
            "/api/v1/tasks/bulk/archive",
            headers=headers,
            json={"task_ids": task_ids},
        )
        assert response.status_code == 200

    def test_bulk_restore_archive(self, client, db, auth_headers):
        """Test bulk restore archived tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        client.post("/api/v1/tasks/bulk/archive", headers=headers, json={"task_ids": task_ids})

        response = client.post(
            "/api/v1/tasks/bulk/restore-archive",
            headers=headers,
            json={"task_ids": task_ids},
        )
        assert response.status_code == 200

    def test_bulk_restore(self, client, db, auth_headers):
        """Test bulk restore soft-deleted tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        client.delete("/api/v1/tasks/bulk", headers=headers, json={"task_ids": task_ids})

        response = client.post(
            "/api/v1/tasks/bulk/restore",
            headers=headers,
            json={"task_ids": task_ids},
        )
        assert response.status_code == 200

    def test_bulk_labels_assign(self, client, db, auth_headers):
        """Test bulk assign labels to tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        label_resp = client.post(
            "/api/v1/labels", headers=headers, json={"name": "bulk-label"}
        )
        label_id = label_resp.get_json()["label"]["id"]

        response = client.post(
            "/api/v1/tasks/bulk/labels",
            headers=headers,
            json={"task_ids": task_ids, "label_id": label_id, "action": "assign"},
        )
        assert response.status_code == 200

    def test_bulk_update(self, client, db, auth_headers):
        """Test bulk update tasks."""
        headers, _ = auth_headers
        task_ids = self._create_tasks(client, headers)

        response = client.patch(
            "/api/v1/tasks/bulk",
            headers=headers,
            json={"task_ids": task_ids, "priority": "urgent"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data["status"]
