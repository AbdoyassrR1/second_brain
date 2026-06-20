#!/usr/bin/python3
"""Flask extensions initialized here for use elsewhere."""

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


db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    in_memory_fallback_enabled=True,
)
bcrypt = Bcrypt()
mail = Mail()
jwt = JWTManager()
ma = Marshmallow()

# CORS initialized without resources here; will be configured in app factory
cors = CORS()