#!/usr/bin/python3
"""Tests for health check endpoints."""

import pytest


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""

    def test_health_check(self, client, db):
        """Test /monitor/health endpoint."""
        response = client.get("/api/v1/monitor/health")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"
        assert "uptime_seconds" in data

    def test_readiness_check(self, client, db):
        """Test /monitor/ready endpoint."""
        response = client.get("/api/v1/monitor/ready")
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ready"
