#!/usr/bin/python3
"""Flask extensions initialized here for use elsewhere."""

import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_mail import Mail
from flask_limiter.util import get_remote_address
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import timezone, timedelta
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow


def _limiter_is_enabled():
    """Check if rate limiting is enabled via config."""
    from flask import current_app
    try:
        return current_app.config.get("RATELIMIT_ENABLED", True)
    except RuntimeError:
        return True


db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=os.getenv("RATELIMIT_STORAGE_URL", "redis://localhost:6379/1"),
    in_memory_fallback_enabled=True,
    enabled=_limiter_is_enabled,
)
bcrypt = Bcrypt()
mail = Mail()
jwt = JWTManager()
ma = Marshmallow()

# CORS initialized without resources here; will be configured in app factory
cors = CORS()

# Redis client and cache — initialized in app factory
redis_client = None
cache = None