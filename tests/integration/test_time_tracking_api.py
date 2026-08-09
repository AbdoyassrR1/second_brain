#!/usr/bin/python3
"""Tests for time tracking API endpoints."""


def _create_task(client, headers, title="Time Task"):
    resp = client.post("/api/v1/tasks", headers=headers, json={"title": title})
    return resp.get_json()["task"]["id"]


class TestTimerEndpoints:
    """Test the timer API."""

    def test_start_stop_flow(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)

        resp = client.post(
            "/api/v1/time/timer/start",
            headers=headers,
            json={"task_ids": [task_id], "note": "focus"},
        )
        assert resp.status_code == 201
        timer = resp.get_json()["timer"]
        assert timer["running"] is True
        assert timer["ended_at"] is None
        assert timer["duration_seconds"] is None
        assert len(timer["task_links"]) == 1

        resp = client.get("/api/v1/time/timer/current", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["timer"]["id"] == timer["id"]

        resp = client.post("/api/v1/time/timer/stop", headers=headers)
        assert resp.status_code == 200
        stopped = resp.get_json()["timer"]
        assert stopped["running"] is False
        assert stopped["ended_at"] is not None
        assert stopped["duration_seconds"] is not None

        resp = client.get("/api/v1/time/timer/current", headers=headers)
        assert resp.get_json()["timer"] is None

    def test_start_second_timer_conflict(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        client.post(
            "/api/v1/time/timer/start", headers=headers, json={"task_ids": [task_id]}
        )
        resp = client.post(
            "/api/v1/time/timer/start", headers=headers, json={"task_ids": [task_id]}
        )
        assert resp.status_code == 409
        assert resp.get_json()["error_code"] == "TIMER_ALREADY_RUNNING"

    def test_start_with_invalid_task(self, client, db, auth_headers):
        headers, _ = auth_headers
        resp = client.post(
            "/api/v1/time/timer/start",
            headers=headers,
            json={"task_ids": ["00000000-0000-0000-0000-000000000000"]},
        )
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "TASK_NOT_VALID"

    def test_timer_task_management(self, client, db, auth_headers):
        headers, _ = auth_headers
        t1 = _create_task(client, headers, "A")
        t2 = _create_task(client, headers, "B")
        t3 = _create_task(client, headers, "C")

        client.post("/api/v1/time/timer/start", headers=headers, json={"task_ids": [t1]})

        resp = client.post(
            "/api/v1/time/timer/tasks", headers=headers, json={"task_ids": [t2, t3]}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data["added"]) == {t2, t3}
        assert len(data["timer"]["task_links"]) == 3

        resp = client.delete(f"/api/v1/time/timer/tasks/{t2}", headers=headers)
        assert resp.status_code == 200
        assert {l["task_id"] for l in resp.get_json()["timer"]["task_links"]} == {t1, t3}

    def test_remove_last_task_denied(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        client.post(
            "/api/v1/time/timer/start", headers=headers, json={"task_ids": [task_id]}
        )
        resp = client.delete(
            f"/api/v1/time/timer/tasks/{task_id}", headers=headers
        )
        assert resp.status_code == 400
        assert resp.get_json()["error_code"] == "LAST_TASK_REMOVAL_DENIED"

    def test_stop_without_timer(self, client, db, auth_headers):
        headers, _ = auth_headers
        resp = client.post("/api/v1/time/timer/stop", headers=headers)
        assert resp.status_code == 404
        assert resp.get_json()["error_code"] == "TIMER_NOT_RUNNING"

    def test_timer_requires_auth(self, client, db):
        resp = client.post("/api/v1/time/timer/start", json={"task_ids": []})
        assert resp.status_code == 401


class TestEntryEndpoints:
    """Test the manual time entry API."""

    def _create_entry(self, client, headers, task_id):
        return client.post(
            "/api/v1/time/entries",
            headers=headers,
            json={
                "task_ids": [task_id],
                "started_at": "2026-01-01T10:00:00Z",
                "ended_at": "2026-01-01T11:00:00Z",
                "note": "manual",
            },
        )

    def test_create_and_get_entry(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)

        resp = self._create_entry(client, headers, task_id)
        assert resp.status_code == 201
        entry = resp.get_json()["entry"]
        assert entry["running"] is False
        assert entry["duration_seconds"] == 3600
        assert entry["task_links"][0]["allocated_seconds"] == 3600

        resp = client.get(f"/api/v1/time/entries/{entry['id']}", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["entry"]["id"] == entry["id"]

    def test_create_entry_invalid_range(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        resp = client.post(
            "/api/v1/time/entries",
            headers=headers,
            json={
                "task_ids": [task_id],
                "started_at": "2026-01-01T11:00:00Z",
                "ended_at": "2026-01-01T10:00:00Z",
            },
        )
        assert resp.status_code == 400

    def test_list_entries(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        self._create_entry(client, headers, task_id)

        resp = client.get("/api/v1/time/entries", headers=headers)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_update_entry(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        entry_id = self._create_entry(client, headers, task_id).get_json()["entry"]["id"]

        resp = client.patch(
            f"/api/v1/time/entries/{entry_id}",
            headers=headers,
            json={"note": "updated"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["entry"]["note"] == "updated"

    def test_update_running_entry_denied(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        client.post(
            "/api/v1/time/timer/start", headers=headers, json={"task_ids": [task_id]}
        )
        entry_id = client.get(
            "/api/v1/time/timer/current", headers=headers
        ).get_json()["timer"]["id"]

        resp = client.patch(
            f"/api/v1/time/entries/{entry_id}",
            headers=headers,
            json={"started_at": "2026-01-01T09:00:00Z"},
        )
        assert resp.status_code == 409
        assert resp.get_json()["error_code"] == "ENTRY_IS_RUNNING"

    def test_delete_entry(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        entry_id = self._create_entry(client, headers, task_id).get_json()["entry"]["id"]

        resp = client.delete(f"/api/v1/time/entries/{entry_id}", headers=headers)
        assert resp.status_code == 200

        resp = client.get(f"/api/v1/time/entries/{entry_id}", headers=headers)
        assert resp.status_code == 404


class TestReportEndpoint:
    """Test the report API."""

    def test_day_report(self, client, db, auth_headers):
        headers, _ = auth_headers
        task_id = _create_task(client, headers)
        client.post(
            "/api/v1/time/entries",
            headers=headers,
            json={
                "task_ids": [task_id],
                "started_at": "2026-03-02T09:00:00Z",
                "ended_at": "2026-03-02T10:00:00Z",
            },
        )

        resp = client.get(
            "/api/v1/time/reports",
            headers=headers,
            query_string={
                "group_by": "day",
                "from": "2026-03-02T00:00:00Z",
                "to": "2026-03-03T00:00:00Z",
            },
        )
        assert resp.status_code == 200
        report = resp.get_json()["report"]
        assert report["group_by"] == "day"
        assert report["totals"]["total_seconds"] == 3600
        assert report["groups"][0]["date"] == "2026-03-02"

    def test_report_invalid_group(self, client, db, auth_headers):
        headers, _ = auth_headers
        resp = client.get(
            "/api/v1/time/reports",
            headers=headers,
            query_string={
                "group_by": "month",
                "from": "2026-03-02T00:00:00Z",
                "to": "2026-03-03T00:00:00Z",
            },
        )
        assert resp.status_code == 400
