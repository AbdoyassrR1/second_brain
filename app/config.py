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
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_REFRESH_TOKEN_REMEMBER_ME_EXPIRES = timedelta(days=30)

    # Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 25))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@backend.local")
    RESET_PASSWORD_URL = os.getenv("RESET_PASSWORD_URL", "http://localhost:5000/api/v1/auth/reset-password")
    EMAIL_VERIFICATION_URL = os.getenv("EMAIL_VERIFICATION_URL", "http://localhost:5000/api/v1/auth/verify-email")

    # Token expiry windows (minutes) for email-link flows
    EMAIL_VERIFICATION_TOKEN_EXPIRES_MINUTES = int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRES_MINUTES", "30"))
    PASSWORD_RESET_TOKEN_EXPIRES_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRES_MINUTES", "15"))

    # Account lockout policy
    MAX_FAILED_LOGIN_ATTEMPTS = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    ACCOUNT_LOCKOUT_MINUTES = int(os.getenv("ACCOUNT_LOCKOUT_MINUTES", "15"))

    # Rate limiting
    RATELIMIT_STORAGE_URL = os.getenv("RATELIMIT_STORAGE_URL", "redis://localhost:6379/1")
    AUTH_RATE_LIMIT = os.getenv("AUTH_RATE_LIMIT", "5 per minute")
    TASK_RATE_LIMIT = os.getenv("TASK_RATE_LIMIT", "10 per minute")

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300"))

    # Celery
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")


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

    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)


class TestingConfig(Config):
    """Testing environment configuration."""

    DEBUG = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=60)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=1)
    MAIL_SUPPRESS_SEND = True

    # Tighter auth windows so lockout/expiry flows are exercisable in tests
    RATELIMIT_ENABLED = False
    RATELIMIT_STORAGE_URL = "memory://"
    AUTH_RATE_LIMIT = "1000 per minute"
    TASK_RATE_LIMIT = "1000 per minute"
    MAX_FAILED_LOGIN_ATTEMPTS = 3
    ACCOUNT_LOCKOUT_MINUTES = 1
    PASSWORD_RESET_TOKEN_EXPIRES_MINUTES = 1


class ProductionConfig(Config):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    # Fail fast rather than running with publicly-known default secrets.
    _INSECURE_SECRETS = {"dev-secret-key-change-in-production", ""}
    if Config.SECRET_KEY in _INSECURE_SECRETS:
        raise RuntimeError("SECRET_KEY must be set to a secure value in production.")
    if Config.JWT_SECRET_KEY in {"jwt-secret-key-change-in-production", ""}:
        raise RuntimeError("JWT_SECRET_KEY must be set to a secure value in production.")

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
