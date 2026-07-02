#!/usr/bin/python3
"""Flask application factory."""

import time
import click
from flask import Flask, g, request
from .extensions import db, migrate, limiter, bcrypt, mail, jwt, cors, ma
from . import config
from app.shared.middleware.middleware import setup_middleware
from app.shared.logging.logging_config import setup_logging
from app.errors.errors import register_error_handlers
from app.errors.jwt import register_jwt_callbacks

from app.shared.metrics import app_startup_time_seconds


def create_app(config_name=None):
    """Create and configure Flask application.

    Args:
        config_name: Configuration environment (development, testing, production).
                     Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Configured Flask application.
    """
    app_startup_start = time.time()
    app = Flask(__name__, static_folder=None) # Disable GET /static/<path:filename>

    # Load configuration
    if config_name is None:
        config_name = "development"
    
    app.config.from_object(config.config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)
    ma.init_app(app)

    # Setup JWT callbacks before routes start using @jwt_required
    register_jwt_callbacks(jwt)

    # Setup structured logging
    setup_logging(app)

    # Setup middleware
    setup_middleware(app)

    # Import User model for JWT
    from app.features.auth.models import User
    from app.features.auth.repository import RoleRepository

    @app.cli.command("seed-roles")
    def seed_roles_command():
        """Seed the default application roles."""

        inserted = RoleRepository.seed_default_roles()
        if inserted:
            click.echo(f"Seeded {inserted} role(s).")
        else:
            click.echo("Default roles already exist.")

    # JWT callbacks
    @jwt.user_identity_loader
    def user_identity_loader(user):
        """Extract user ID for JWT identity."""
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """Load a non-deleted user from JWT identity.

        Soft-deleted users are treated as if they don't exist, so any token
        belonging to a deleted account fails authentication.
        """
        identity = jwt_data["sub"]
        user = User.query.filter_by(id=identity, is_deleted=False).first()
        g.user_id = user.id if user else None
        return user

    # Register error handlers
    register_error_handlers(app)

    # Register blueprints
    register_blueprints(app)

    # Metrics endpoint
    @app.route("/metrics", methods=["GET"])
    def metrics():
        """Prometheus metrics endpoint."""
        # Optionally protect metrics in production
        if app.config.get("METRICS_PROTECT"):
            # Allow by whitelist IPs or a bearer token header
            whitelist = app.config.get("METRICS_WHITELIST_IPS", []) or []
            token = app.config.get("METRICS_AUTH_TOKEN")
            remote = request.remote_addr
            auth_header = request.headers.get("X-Metrics-Token")

            allowed = False
            if whitelist and remote in whitelist:
                allowed = True
            if token and auth_header and auth_header == token:
                allowed = True
            if not allowed:
                from flask import jsonify
                return jsonify({"status": "error", "message": "Forbidden"}), 403

        from prometheus_client import generate_latest
        return generate_latest(), 200, {"Content-Type": "text/plain; charset=utf-8"}

    # Health check for app initialization
    @app.route("/api/v1/health/startup", methods=["GET"])
    def startup_check():
        """Quick startup check."""
        from flask import jsonify
        return jsonify({"status": "ok"}), 200

    # Record startup time
    startup_time = time.time() - app_startup_start
    app_startup_time_seconds.set(startup_time)
    app.logger.info(
        "Application initialized",
        extra={"startup_time_seconds": startup_time}
    )

    return app


def register_blueprints(app):
    """Register all feature blueprints."""
    from app.features import auth_bp, me_bp, tasks_bp, reminders_bp, health_bp, projects_bp, labels_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(me_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(reminders_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(labels_bp)
