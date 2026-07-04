#!/usr/bin/python3
"""Tests for mail service."""

import pytest
from unittest.mock import Mock, patch
from app.features.mail.service import MailService


class TestMailService:
    """Test mail service methods with mocked mail sender."""

    @pytest.fixture
    def mail_service(self, app):
        with app.app_context():
            return MailService()

    def test_send_password_reset_email(self, mail_service, verified_user, monkeypatch):
        """Test sending a password reset email."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients
            sent["body"] = body

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_password_reset_email(verified_user, "reset-token-123")

        assert "Password Reset" in sent["subject"]
        assert verified_user.email in sent["recipients"]
        assert "reset-token-123" in sent["body"]

    def test_send_password_changed_notification(self, mail_service, verified_user, monkeypatch):
        """Test sending password changed notification."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_password_changed_notification(verified_user)

        assert "Changed" in sent["subject"]
        assert verified_user.email in sent["recipients"]

    def test_send_welcome_email(self, mail_service, verified_user, monkeypatch):
        """Test sending welcome email."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_welcome_email(verified_user)

        assert "Welcome" in sent["subject"]
        assert verified_user.email in sent["recipients"]

    def test_send_email_verification(self, mail_service, verified_user, monkeypatch):
        """Test sending email verification."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients
            sent["body"] = body

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_email_verification(verified_user, "verify-token-456")

        assert "Verify" in sent["subject"]
        assert verified_user.email in sent["recipients"]
        assert "verify-token-456" in sent["body"]

    def test_send_email_verification_custom_recipient(self, mail_service, verified_user, monkeypatch):
        """Test sending email verification to a custom recipient."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["recipients"] = recipients

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_email_verification(verified_user, "token", recipient_email="custom@example.com")
        assert "custom@example.com" in sent["recipients"]

    def test_send_otp_email(self, mail_service, verified_user, monkeypatch):
        """Test sending OTP email."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients
            sent["body"] = body

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_otp_email(verified_user, "123456")

        assert "verification code" in sent["subject"].lower()
        assert verified_user.email in sent["recipients"]
        assert "123456" in sent["body"]

    def test_send_alert(self, mail_service, verified_user, monkeypatch):
        """Test sending alert email."""
        sent = {}

        def fake_send(subject, recipients, body, html=None):
            sent["subject"] = subject
            sent["recipients"] = recipients

        monkeypatch.setattr(mail_service, "send_email", fake_send)

        mail_service.send_alert(verified_user, "security", "Suspicious login detected")

        assert "Alert" in sent["subject"]
        assert verified_user.email in sent["recipients"]
