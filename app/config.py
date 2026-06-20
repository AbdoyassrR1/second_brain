#!/usr/bin/python3
"""Application configuration for different environments."""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@backend.local")
    RESET_PASSWORD_URL = os.getenv("RESET_PASSWORD_URL", "http://localhost:5000/api/v1/auth/reset-password")
    EMAIL_VERIFICATION_URL = os.getenv("EMAIL_VERIFICATION_URL", "http://localhost:5000/api/v1/auth/verify-email")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    # Observability / metrics
    METRICS_PROTECT = os.getenv("METRICS_PROTECT", "false").lower() == "true"
    METRICS_AUTH_TOKEN = os.getenv("METRICS_AUTH_TOKEN")
    METRICS_WHITELIST_IPS = os.getenv("METRICS_WHITELIST_IPS", "").split(",") if os.getenv("METRICS_WHITELIST_IPS") else []

    # Service metadata
    SERVICE_NAME = os.getenv("SERVICE_NAME", "second_brain")
    SERVICE_VERSION = os.getenv("SERVICE_VERSION", "0.0.0")
    ENVIRONMENT = os.getenv("FLASK_ENV", "development")

    # Logging/retention
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))


class DevelopmentConfig(Config):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    
    if all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    else:
        # Fallback to environment variable
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_ECHO = True

    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=60)
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False
    
    # Production DB must be specified
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")
    DB_NAME = os.getenv("DB_NAME")
    
    if all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
        SQLALCHEMY_DATABASE_URI = f"mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    else:
        # Fallback to environment variable
        SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",")


# Configuration dictionary for easy lookup
config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
