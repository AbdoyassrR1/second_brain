#!/usr/bin/python3
from flask import current_app
from flask_mail import Message
from app.extensions import mail
from app.features.auth.models import User
from typing import List, Optional


class MailService:

    def send_email(self, subject: str, recipients: List[str], body: str, html: Optional[str] = None):
        """
        Send a basic email.
        
        Args:
            subject: Email subject
            recipients: List of recipient email addresses
            body: Plain text body
            html: Optional HTML body
        """
        msg = Message(subject, recipients=recipients)
        msg.body = body
        if html:
            msg.html = html
        mail.send(msg)
    
    def send_password_reset_email(self, user: User, token: str):
        """
        Send password reset email to user.
        
        Args:
            user: User object
            token: Reset token string
        """
        reset_url = f"{current_app.config.get('RESET_PASSWORD_URL')}?token={token}"
        
        subject = "Password Reset Request"
        body = f"""Hello {user.username},

You have requested to reset your password. Please use the following link to reset it:

{reset_url}


This link will expire in 15 minutes.

If you did not make this request, please ignore this email and your password will remain unchanged.

Best regards,
The Second Brain Team
"""
        
        self.send_email(subject, [user.email], body)

    def send_password_changed_notification(self, user: User):
        """
        Notify user that their password was changed successfully.
        
        Args:
            user: User object
        """
        subject = "Password Changed Successfully"
        body = f"""Hello {user.username},

Your password has been changed successfully.

If you did not make this change, please contact support immediately.

Best regards,
The Second Brain Team
"""
        
        self.send_email(subject, [user.email], body)

    def send_welcome_email(self, user: User):
        """
        Send welcome email to newly registered user.
        
        Args:
            user: User object
        """
        subject = "Welcome to Second Brain!"
        body = f"""Hello {user.username},

Welcome to Second Brain! Your account has been created successfully.

We're excited to have you on board.

Best regards,
The Second Brain Team
"""
        
        self.send_email(subject, [user.email], body)

    def send_email_verification(self, user: User, token: str, recipient_email: Optional[str] = None):
        """
        Send an email verification link to the user.

        Args:
            user: User object
            token: Verification token string
            recipient_email: Optional email address to send to instead of user.email
        """
        verification_url = f"{current_app.config.get('EMAIL_VERIFICATION_URL')}?token={token}"

        subject = "Verify your email address"
        body = f"""Hello {user.username},

Please verify your email address by opening the following link:

{verification_url}

This link will expire in 30 minutes.

If you did not create this account, you can ignore this email.

Best regards,
The Second Brain Team
"""

        self.send_email(subject, [recipient_email or user.email], body)

    def send_otp_email(self, user: User, otp_code: str):
        """Send a short-lived login OTP to the user."""
        subject = "Your Second Brain verification code"
        body = f"""Hello {user.username},

Your one-time verification code is: {otp_code}

This code expires in 5 minutes. If you did not try to sign in, you can ignore this email.

Best regards,
The Second Brain Team
"""

        self.send_email(subject, [user.email], body)

    def send_alert(self, user: User, alert_type: str, message: str):
        """
        Send a generic alert/notification to user.
        
        Args:
            user: User object
            alert_type: Type of alert (e.g., 'security', 'update', 'warning')
            message: Alert message
        """
        subject = f"Alert: {alert_type.capitalize()}"
        body = f"""Hello {user.username},

{message}

Best regards,
The Second Brain Team
"""
        
        self.send_email(subject, [user.email], body)