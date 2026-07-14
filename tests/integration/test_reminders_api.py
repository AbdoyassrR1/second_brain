import pytest
from datetime import datetime, timedelta


class TestReminderCreate:
    def test_create_reminder_success(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task with Reminder"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        response = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["status"] == "success"
        assert data["reminder"]["task_id"] == task_id

    def test_create_reminder_unauthorized(self, client, db):
        response = client.post(
            "/api/v1/reminders",
            json={"task_id": "some-id", "reminder_time": datetime.utcnow().isoformat()},
        )
        assert response.status_code == 401

    def test_create_reminder_missing_fields(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={},
        )
        assert response.status_code == 400

    def test_create_reminder_non_json(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.post(
            "/api/v1/reminders",
            headers=headers,
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code == 415


class TestReminderList:
    def test_list_reminders_empty(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.get("/api/v1/reminders", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_reminders_with_data(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )

        response = client.get("/api/v1/reminders", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["task_id"] == task_id

    def test_list_reminders_pagination(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        for _ in range(3):
            client.post(
                "/api/v1/reminders",
                headers=headers,
                json={"task_id": task_id, "reminder_time": future},
            )

        response = client.get(
            "/api/v1/reminders?page=1&per_page=2", headers=headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 3
        assert len(data["items"]) == 2
        assert data["pages"] == 2

    def test_list_reminders_unauthorized(self, client, db):
        response = client.get("/api/v1/reminders")
        assert response.status_code == 401


class TestReminderGet:
    def test_get_reminder_success(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        response = client.get(f"/api/v1/reminders/{reminder_id}", headers=headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data["reminder"]["id"] == reminder_id
        assert data["reminder"]["task_id"] == task_id

    def test_get_reminder_not_found(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.get("/api/v1/reminders/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_get_reminder_unauthorized(self, client, db, auth_headers):
        headers, user_id = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        response = client.get(f"/api/v1/reminders/{reminder_id}")
        assert response.status_code == 401


class TestReminderUpdate:
    def test_update_reminder_time(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        new_time = (datetime.utcnow() + timedelta(hours=2)).isoformat()
        response = client.patch(
            f"/api/v1/reminders/{reminder_id}",
            headers=headers,
            json={"reminder_time": new_time},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["reminder"]["id"] == reminder_id

    def test_update_reminder_not_found(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.patch(
            "/api/v1/reminders/nonexistent-id",
            headers=headers,
            json={"reminder_time": datetime.utcnow().isoformat()},
        )
        assert response.status_code == 404

    def test_update_reminder_unauthorized(self, client, db, auth_headers):
        headers, user_id = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        response = client.patch(
            f"/api/v1/reminders/{reminder_id}",
            headers=headers,
            json={"reminder_time": future},
        )
        assert response.status_code == 200

    def test_update_reminder_non_json(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.patch(
            "/api/v1/reminders/some-id",
            headers=headers,
            data="not json",
            content_type="text/plain",
        )
        assert response.status_code == 415


class TestReminderDelete:
    def test_delete_reminder_success(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        response = client.delete(f"/api/v1/reminders/{reminder_id}", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["status"] == "success"

        get_resp = client.get(f"/api/v1/reminders/{reminder_id}", headers=headers)
        assert get_resp.status_code == 404

    def test_delete_reminder_not_found(self, client, db, auth_headers):
        headers, _ = auth_headers
        response = client.delete("/api/v1/reminders/nonexistent-id", headers=headers)
        assert response.status_code == 404

    def test_delete_reminder_unauthorized(self, client, db, auth_headers):
        headers, user_id = auth_headers
        task_resp = client.post(
            "/api/v1/tasks", headers=headers, json={"title": "Task"}
        )
        task_id = task_resp.get_json()["task"]["id"]

        future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        create_resp = client.post(
            "/api/v1/reminders",
            headers=headers,
            json={"task_id": task_id, "reminder_time": future},
        )
        reminder_id = create_resp.get_json()["reminder"]["id"]

        response = client.delete(f"/api/v1/reminders/{reminder_id}")
        assert response.status_code == 401
