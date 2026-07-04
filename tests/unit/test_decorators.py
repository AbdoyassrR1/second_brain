#!/usr/bin/python3
"""Tests for shared decorators."""

import json
import pytest
from flask import Flask
from app.shared.decorators import require_json_body
from app.shared.exceptions import UnauthorizedError
from unittest.mock import Mock


class TestRequireJsonBody:
    """Test require_json_body decorator."""

    @pytest.fixture
    def app(self):
        """Create a minimal Flask app for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        return app

    def test_valid_json(self, app):
        """Test decorator with valid JSON body."""
        @require_json_body()
        def view(json_data):
            return {"status": "ok", "data": json_data}

        with app.test_request_context(
            "/test", method="POST",
            data=json.dumps({"key": "value"}),
            content_type="application/json",
        ):
            result = view()
            assert result["status"] == "ok"
            assert result["data"]["key"] == "value"

    def test_non_json_content_type(self, app):
        """Test decorator with non-JSON content type."""
        @require_json_body()
        def view(json_data):
            return {"status": "ok"}

        with app.test_request_context(
            "/test", method="POST",
            data="not json",
            content_type="text/plain",
        ):
            response, status = view()
            assert status == 415
            data = response.get_json()
            assert "application/json" in data["message"].lower()

    def test_malformed_json(self, app):
        """Test decorator with malformed JSON."""
        @require_json_body()
        def view(json_data):
            return {"status": "ok"}

        with app.test_request_context(
            "/test", method="POST",
            data="{bad json",
            content_type="application/json",
        ):
            response, status = view()
            assert status == 400
            data = response.get_json()
            assert "Malformed" in data["message"]

    def test_non_object_json(self, app):
        """Test decorator with non-object JSON (list)."""
        @require_json_body()
        def view(json_data):
            return {"status": "ok"}

        with app.test_request_context(
            "/test", method="POST",
            data=json.dumps(["item1", "item2"]),
            content_type="application/json",
        ):
            response, status = view()
            assert status == 400
            data = response.get_json()
            assert "object" in data["message"].lower()

    def test_custom_payload_key(self, app):
        """Test decorator with custom payload key."""
        @require_json_body(payload_key="custom_data")
        def view(custom_data):
            return {"status": "ok", "data": custom_data}

        with app.test_request_context(
            "/test", method="POST",
            data=json.dumps({"key": "value"}),
            content_type="application/json",
        ):
            result = view()
            assert result["status"] == "ok"
            assert result["data"]["key"] == "value"
