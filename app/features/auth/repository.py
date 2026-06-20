#!/usr/bin/python3
"""Auth repository for database operations."""

from datetime import datetime
from sqlalchemy import and_
from app.extensions import db
from .models import User, Role, VerificationToken


class UserRepository:
    """Repository for User database operations."""

    @staticmethod
    def find_by_username(username):
        """Find user by username."""
        return User.query.filter_by(username=username).first()

    @staticmethod
    def find_by_email(email):
        """Find user by email."""
        return User.query.filter_by(email=email).first()

    @staticmethod
    def find_by_phone_number(phone_number):
        """Find user by phone number."""
        return User.query.filter_by(phone_number=phone_number).first()

    @staticmethod
    def find_by_id(user_id):
        """Find user by ID."""
        return User.query.filter_by(id=user_id).first()

    @staticmethod
    def create(username, email, password, phone_number, role_id=1):
        """Create and save a new user."""
        user = User(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
            role_id=role_id,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update(user_id, **kwargs):
        """Update user fields."""
        user = User.query.filter_by(id=user_id).first()
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.session.commit()
        return user


class RoleRepository:
    """Repository for Role database operations."""

    @staticmethod
    def find_by_id(role_id):
        """Find role by ID."""
        return Role.query.filter_by(id=role_id).first()

    @staticmethod
    def find_by_name(name):
        """Find role by name."""
        return Role.query.filter_by(name=name).first()

    @staticmethod
    def create(name, description):
        """Create and save a new role."""
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
        return role

    @staticmethod
    def seed_default_roles():
        """Insert the default roles if they do not already exist."""

        roles = {
            "customer": "Standard user role",
            "admin": "Administrator role with full permissions",
        }

        inserted = 0
        for name, description in roles.items():
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=description))
                inserted += 1

        if inserted:
            db.session.commit()

        return inserted

    @staticmethod
    def insert_rols():
        """Backward-compatible alias for the old misspelled method name."""

        return RoleRepository.seed_default_roles()


class VerificationTokenRepository:
    """Repository for verification token database operations."""

    @staticmethod
    def create(user_id, token, expiry_date):
        """Create a verification token record."""
        verification_token = VerificationToken(
            user_id=user_id,
            token=token,
            expiry_date=expiry_date,
            is_used=False,
        )
        db.session.add(verification_token)
        db.session.commit()
        return verification_token

    @staticmethod
    def find_by_token(token):
        """Find a verification token by its value."""
        return VerificationToken.query.filter_by(token=token).first()

    @staticmethod
    def find_active_by_token(token):
        """Find an unused, unexpired verification token by value."""
        return VerificationToken.query.filter(
            and_(
                VerificationToken.token == token,
                VerificationToken.is_used.is_(False),
                VerificationToken.expiry_date > datetime.utcnow(),
            )
        ).first()

    @staticmethod
    def mark_used(token_record):
        """Mark a verification token as used."""
        if token_record:
            token_record.is_used = True
            db.session.commit()
        return token_record

    @staticmethod
    def invalidate_user_tokens(user_id):
        """Mark all unused verification tokens for a user as used."""
        tokens = VerificationToken.query.filter_by(user_id=user_id, is_used=False).all()
        for token in tokens:
            token.is_used = True
        if tokens:
            db.session.commit()
        return tokens