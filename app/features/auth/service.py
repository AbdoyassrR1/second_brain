#!/usr/bin/python3
"""Auth service for business logic."""

from datetime import datetime, timedelta
import secrets
from flask import current_app
from app.shared.exceptions import (
    ValidationError,
    UnauthorizedError,
    ConflictError,
    NotFoundError,
)
from app.shared.logging.audit_log import log_registration, log_login_attempt, log_profile_update
from app.extensions import db
from .repository import UserRepository, RoleRepository, VerificationTokenRepository
from app.features.mail.service import MailService


class AuthService:
    """Service for authentication and user management."""

    def __init__(self):
        self.user_repo = UserRepository()
        self.role_repo = RoleRepository()
        self.mail_service = MailService()
        self.verification_token_repo = VerificationTokenRepository()

    def register(self, username, email, password, phone_number, role="customer"):
        """Register a new user.

        Args:
            username: Unique username
            email: Unique email
            password: Plain text password (will be hashed)
            phone_number: Unique phone number
            role: User role (default is "customer")

        Returns:
            User object

        Raises:
            ValidationError: If input is invalid
            ConflictError: If username/email/phone already exists
        """

        # Check for duplicates
        if self.user_repo.find_by_username(username):
            raise ConflictError("Username already exists")
        if self.user_repo.find_by_email(email):
            raise ConflictError("Email already exists")
        if self.user_repo.find_by_phone_number(phone_number):
            raise ConflictError("Phone number already exists")

        # Get default role
        role_record = self.role_repo.find_by_name(role)
        if not role_record:
            raise NotFoundError(f"Role '{role}' not found")
        
        # Create user
        user = self.user_repo.create(username, email, password, phone_number, role_record.id)
        
        # Log registration audit event
        log_registration(user.id, username, email)

        # Send verification email after creating the account.
        self.send_email_verification(email)
        
        return user

    def send_email_verification(self, email):
        """Send email verification for an existing user.

        Args:
            email: Unique email

        Returns:
            User object

        Raises:
            NotFoundError: If user is not found
            ConflictError: If user is already verified
        """
        user = self.user_repo.find_by_email(email)
        if not user:
            raise NotFoundError("User not found")

        if user.is_verified:
            raise ConflictError("Email is already verified")

        token = secrets.token_urlsafe(32)
        expiry_minutes = current_app.config.get("EMAIL_VERIFICATION_TOKEN_EXPIRES_MINUTES", 30)
        expiry_date = datetime.utcnow() + timedelta(minutes=expiry_minutes)

        self.verification_token_repo.invalidate_user_tokens(user.id)
        self.verification_token_repo.create(user.id, token, expiry_date)
        self.mail_service.send_email_verification(user, token)

        return user

    def verify_email(self, token):
        """Verify a user's email address using a verification token."""
        verification_token = self.verification_token_repo.find_active_by_token(token)
        if not verification_token:
            raise NotFoundError("Invalid or expired verification token")

        user = verification_token.user
        if not user:
            raise NotFoundError("User not found")

        user.is_verified = True
        user.verified_at = datetime.utcnow()
        verification_token.is_used = True
        db.session.commit()

        return user

    def login(self, password, email=None, username=None):
        """Authenticate user and return user object.

        Args:
            password: Plain text password
            email: User's email
            username: User's username

        Returns:
            User object if authentication successful

        Raises:
            UnauthorizedError: If credentials are invalid
        """
        from app.shared.metrics import user_logins_total
        
        identity = email or username
        if email:
            user = self.user_repo.find_by_email(email)
        else:
            user = self.user_repo.find_by_username(username)

        if not user:
            log_login_attempt(identity, False, reason="user_not_found")
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("Invalid email or password")

        if not user.check_password(password):
            log_login_attempt(identity, False, reason="invalid_password")
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("Invalid email or password")

        if not user.is_verified:
            log_login_attempt(identity, False, reason="user_not_verified")
            user_logins_total.labels(success="false").inc()
            raise UnauthorizedError("User account is not verified")

        # Update last login
        user.last_login = datetime.now()
        db.session.commit()
        
        # Log successful login
        log_login_attempt(identity, True)
        user_logins_total.labels(success="true").inc()
        
        return user

    def get_user_profile(self, user_id):
        """Get user profile by ID.

        Args:
            user_id: User ID

        Returns:
            User object

        Raises:
            NotFoundError: If user not found
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def update_user_profile(self, user_id, **kwargs):
        """Update user profile fields.

        Args:
            user_id: User ID
            **kwargs: Fields to update (username, email, password, etc.)

        Returns:
            Updated user object

        Raises:
            NotFoundError: If user not found
            ValidationError: If update is invalid
        """
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")

        # Handle password updates
        if "password" in kwargs:
            password = kwargs.pop("password")
            if len(password) < 8:
                raise ValidationError("Password must be at least 8 characters")
            user.set_password(password)

        # Update other fields
        if "username" in kwargs:
            if self.user_repo.find_by_username(kwargs["username"]):
                raise ConflictError("Username already exists")

        # Perform update
        updated_user = self.user_repo.update(user_id, **kwargs)
        
        # Log profile update audit event
        log_profile_update(user_id, kwargs)
        
        return updated_user
