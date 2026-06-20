#!/usr/bin/python3
"""Auth routes and endpoints."""

from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from app.shared.exceptions import AppError, ConflictError
from app.shared.decorators import require_json_body
from .service import AuthService
from .schema import (
    UserRegistrationSchema,
    UserLoginSchema,
    UserProfileSchema,
    SendEmailVerificationSchema,
    VerifyEmailSchema,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
auth_service = AuthService()
registration_schema = UserRegistrationSchema()
login_schema = UserLoginSchema()
profile_schema = UserProfileSchema()
send_verification_schema = SendEmailVerificationSchema()
verify_email_schema = VerifyEmailSchema()


@auth_bp.route("/register", methods=["POST"])
@require_json_body()
def register(json_data):
    """Register a new user."""
    try:
        data = registration_schema.load(json_data)

        user = auth_service.register(**data)


        return (
            jsonify(
                {
                    "status": "success",
                    "message": "User registered successfully",
                    "user": registration_schema.dump(user),
                }
            ),
            201,
        )
    except AppError as e:
        abort(e.status_code, description=e.message)


@auth_bp.route("/send-email-verification", methods=["POST"])
@require_json_body()
def send_email_verification(json_data):
    """Send an email verification link to a user."""
    try:
        data = send_verification_schema.load(json_data)
        user = auth_service.send_email_verification(data["email"])
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Verification email sent successfully",
                    "user": profile_schema.dump(user),
                }
            ),
            200,
        )
    except AppError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.messages}), 400


@auth_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    """Verify a user's email using a token."""
    try:
        if request.method == "GET":
            data = verify_email_schema.load({"token": request.args.get("token")})
        else:
            data = verify_email_schema.load(request.get_json(silent=True) or {})
        user = auth_service.verify_email(data["token"])
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Email verified successfully",
                    "user": profile_schema.dump(user),
                }
            ),
            200,
        )
    except AppError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.messages}), 400


@auth_bp.route("/login", methods=["POST"])
@require_json_body()
def login(json_data):
    """Login user with username and password."""
    try:
        data = login_schema.load(json_data)

        user = auth_service.login(**data)

        # Generate tokens
        access_token = create_access_token(identity=user)
        refresh_token = create_refresh_token(identity=user)

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Login successful",
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "user": profile_schema.dump(user),
                }
            ),
            200,
        )
    except AppError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.messages}), 400
    except Exception:
        raise


@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        user_id = get_jwt_identity()
        user = auth_service.get_user_profile(user_id)
        return jsonify({"status": "success", "user": profile_schema.dump(user)}), 200
    except AppError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.messages}), 400
    except Exception:
        raise


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
@require_json_body()
def update_profile(json_data):
    """Update current user profile."""
    try:
        user_id = get_jwt_identity()

        user = auth_service.update_user_profile(user_id, **json_data)
        return jsonify({"status": "success", "user": profile_schema.dump(user)}), 200
    except AppError as e:
        return jsonify({"status": "error", "message": e.message}), e.status_code
    except ValidationError as e:
        return jsonify({"status": "error", "message": e.messages}), 400
    except Exception:
        raise
