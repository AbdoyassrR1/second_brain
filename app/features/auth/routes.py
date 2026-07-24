#!/usr/bin/python3
"""Auth routes and endpoints."""

from datetime import datetime, UTC

from flask import Blueprint, request, jsonify, current_app
from app.extensions import limiter
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    decode_token,
)

from app.shared.decorators import require_json_body
from .service import AuthService
from .schema import (
    UserRegistrationSchema,
    UserLoginSchema,
    UserProfileSchema,
    SendEmailVerificationSchema,
    VerifyEmailSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
    ChangePasswordSchema,
    ChangeEmailSchema,
    UpdateProfileSchema,
    UserDeviceSchema,
    Enable2FASchema,
    Disable2FASchema,
    VerifyOTPSchema,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")
me_bp = Blueprint("me", __name__, url_prefix="/api/v1/me")

auth_service = AuthService()

# Schema instances (reuse across requests)
registration_schema = UserRegistrationSchema()
login_schema = UserLoginSchema()
profile_schema = UserProfileSchema()
send_verification_schema = SendEmailVerificationSchema()
verify_email_schema = VerifyEmailSchema()
forgot_password_schema = ForgotPasswordSchema()
reset_password_schema = ResetPasswordSchema()
change_password_schema = ChangePasswordSchema()
change_email_schema = ChangeEmailSchema()
update_profile_schema = UpdateProfileSchema()
device_schema = UserDeviceSchema()
enable_2fa_schema = Enable2FASchema()
disable_2fa_schema = Disable2FASchema()
verify_otp_schema = VerifyOTPSchema()


def _issue_tokens(user, remember_me=False):
    """Create an access + refresh token pair and record metrics.

    Both tokens carry the user's ``token_version`` as a claim so that a version
    bump (logout-all / password change / account deletion) retroactively
    revokes every previously-issued token.
    """
    from app.shared.metrics import jwt_token_issued_total

    extra_claims = {
        "role": user.role.name if user.role else None,
        "ver": user.token_version,
        "2fa_pending": False,
    }
    access_token = create_access_token(identity=user, additional_claims=extra_claims)
    refresh_delta_key = (
        "JWT_REFRESH_TOKEN_REMEMBER_ME_EXPIRES"
        if remember_me
        else "JWT_REFRESH_TOKEN_EXPIRES"
    )
    refresh_token = create_refresh_token(
        identity=user,
        expires_delta=current_app.config.get(refresh_delta_key),
        additional_claims=extra_claims,
    )

    jwt_token_issued_total.labels(token_type="access").inc()
    jwt_token_issued_total.labels(token_type="refresh").inc()
    return access_token, refresh_token


# ─── Registration ────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def register(json_data):
    """Register a new user."""
    data = registration_schema.load(json_data)
    user = auth_service.register(**data)
    return (
        jsonify(
            {
                "status": "success",
                "message": "User registered successfully",
                "user": profile_schema.dump(user),
            }
        ),
        201,
    )


# ─── Login ───────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def login(json_data):
    """Login user with username/email and password."""
    data = login_schema.load(json_data)
    remember_me = data.pop("remember_me", False)

    auth_result = auth_service.login(**data)

    if isinstance(auth_result, dict) and auth_result.get("status") == "2fa_required":
        return jsonify(auth_result), 200

    user = auth_result
    
    access_token, refresh_token = _issue_tokens(user, remember_me=remember_me)

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


# ─── Refresh ─────────────────────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Rotate the refresh token: revoke the old one, issue a new pair."""
    user_id = get_jwt_identity()
    refresh_claims = get_jwt()
    refresh_jti = refresh_claims["jti"]
    old_expires_at = datetime.fromtimestamp(
        refresh_claims.get("exp", 0), tz=UTC
    )

    user = auth_service.rotate_refresh_token(user_id, refresh_jti, old_expires_at)
    access_token, new_refresh_token = _issue_tokens(user)

    return (
        jsonify(
            {
                "status": "success",
                "access_token": access_token,
                "refresh_token": new_refresh_token,
            }
        ),
        200,
    )


# ─── Logout ──────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Revoke the current access token (effectively logging the user out)."""
    user_id = get_jwt_identity()
    token_data = get_jwt()
    jti = token_data["jti"]
    expires_at = datetime.fromtimestamp(token_data.get("exp", 0), tz=UTC)

    auth_service.revoke_token(jti, "access", user_id, expires_at)
    return jsonify({"status": "success", "message": "Logout successful"}), 200


@auth_bp.route("/logout-all", methods=["POST"])
@jwt_required()
def logout_all():
    """Revoke all tokens for the current user."""
    user_id = get_jwt_identity()
    auth_service.revoke_all_tokens(user_id)
    return jsonify({"status": "success", "message": "Logged out from all devices"}), 200


# ─── Email Verification ──────────────────────────────────────────────

@auth_bp.route("/send-email-verification", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def send_email_verification(json_data):
    """Send an email verification link to a user."""
    data = send_verification_schema.load(json_data)
    user = auth_service.send_email_verification(data["email"])
    return (
        jsonify(
            {
                "status": "success",
                "message": "If that email exists, a verification email has been sent.",
            }
        ),
        200,
    )


@auth_bp.route("/verify-email", methods=["GET", "POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
def verify_email():
    """Verify a user's email using a token."""
    if request.method == "GET":
        data = verify_email_schema.load({"token": request.args.get("token")})
    else:
        # Don't enforce JSON content-type for this convenience endpoint.
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


# ─── Password Management ─────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def forgot_password(json_data):
    """Request a password reset email. Always returns 200 (no enumeration)."""
    data = forgot_password_schema.load(json_data)
    auth_service.request_password_reset(data["email"])
    return (
        jsonify(
            {
                "status": "success",
                "message": "If that email exists, a reset link has been sent.",
            }
        ),
        200,
    )


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def reset_password(json_data):
    """Reset password using a token from the forgot-password email."""
    data = reset_password_schema.load(json_data)
    user = auth_service.reset_password(data["token"], data["new_password"])
    return (
        jsonify(
            {
                "status": "success",
                "message": "Password reset successfully",
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )


# ─── Account Management (/me) ────────────────────────────────────────

@me_bp.route("", methods=["GET"])
@jwt_required()
def get_me():
    """Get the current user's account."""
    user_id = get_jwt_identity()
    user = auth_service.get_user_profile(user_id)
    return jsonify({"status": "success", "user": profile_schema.dump(user)}), 200


@me_bp.route("", methods=["PATCH"])
@jwt_required()
@require_json_body()
def update_me(json_data):
    """Update the current user's profile (validated fields only)."""
    user_id = get_jwt_identity()
    data = update_profile_schema.load(json_data)
    user = auth_service.update_user_profile(user_id, **data)
    return jsonify({"status": "success", "user": profile_schema.dump(user)}), 200


@me_bp.route("", methods=["DELETE"])
@jwt_required()
def delete_me():
    """Soft-delete the current user's account."""
    user_id = get_jwt_identity()
    auth_service.delete_account(user_id)
    return jsonify({"status": "success", "message": "Account deleted"}), 200


@me_bp.route("/devices", methods=["GET"])
@jwt_required()
def list_devices():
    """List all recorded devices/sessions for the current user."""
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    p = auth_service.list_devices(user_id, page=page, per_page=per_page)
    return (
        jsonify(
            {
                "status": "success",
                "items": device_schema.dump(p.items, many=True),
                "total": p.total,
                "page": p.page,
                "per_page": p.per_page,
                "pages": p.pages,
                "next_page": p.next_num,
                "prev_page": p.prev_num,
            }
        ),
        200,
    )


@me_bp.route("/devices/<device_id>", methods=["DELETE"])
@jwt_required()
def revoke_device(device_id):
    """Revoke a specific device."""
    user_id = get_jwt_identity()
    auth_service.revoke_device(user_id, device_id)
    return jsonify({"status": "success", "message": "Device revoked"}), 200


@me_bp.route("/change-password", methods=["POST"])
@jwt_required()
@require_json_body()
def change_password(json_data):
    """Change password while logged in (requires current password)."""
    data = change_password_schema.load(json_data)
    user_id = get_jwt_identity()
    user = auth_service.change_password(
        user_id, data["current_password"], data["new_password"]
    )
    return (
        jsonify(
            {
                "status": "success",
                "message": "Password changed successfully. Please log in again.",
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )


@me_bp.route("/change-email", methods=["POST"])
@jwt_required()
@require_json_body()
def change_email(json_data):
    """Change email while logged in and send verification to the new address."""
    data = change_email_schema.load(json_data)
    user_id = get_jwt_identity()
    user = auth_service.change_email(
        user_id, data["current_password"], data["new_email"]
    )
    return (
        jsonify(
            {
                "status": "success",
                "message": "Verification email sent to the new address.",
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )


# ─── 2FA Management ──────────────────────────────────────────────────

@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit(lambda: current_app.config.get("AUTH_RATE_LIMIT", "5 per minute"))
@require_json_body()
def verify_otp(json_data):
    """Verify OTP and issue full tokens if valid."""
    data = verify_otp_schema.load(json_data)
    otp_code = data["otp_code"]
    pending_token = data.get("pending_token")

    if not pending_token:
        return jsonify({"status": "error", "message": "Missing 2FA pending token"}), 401

    try:
        decoded_token = decode_token(pending_token)
        if not decoded_token.get("2fa_pending"):
            return jsonify({"status": "error", "message": "Invalid 2FA pending token"}), 401
        user_id = decoded_token.get("sub")
    except Exception:
        return jsonify({"status": "error", "message": "Invalid or expired 2FA pending token"}), 401

    user = auth_service.verify_otp(user_id, otp_code)
    access_token, refresh_token = _issue_tokens(user)  # Issue full tokens

    return (
        jsonify(
            {
                "status": "success",
                "message": "OTP verified, login complete",
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )


@me_bp.route("/enable-2fa", methods=["POST"])
@jwt_required()
@require_json_body()
def enable_2fa(json_data):
    """Enable 2FA for the current user."""
    data = enable_2fa_schema.load(json_data)
    user_id = get_jwt_identity()
    user = auth_service.enable_2fa(user_id, data["current_password"])
    return (
        jsonify(
            {
                "status": "success",
                "message": "Two-factor authentication enabled. Please log in again.",
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )


@me_bp.route("/disable-2fa", methods=["POST"])
@jwt_required()
@require_json_body()
def disable_2fa(json_data):
    """Disable 2FA for the current user."""
    data = disable_2fa_schema.load(json_data)
    user_id = get_jwt_identity()
    user = auth_service.disable_2fa(user_id, data["current_password"])
    return (
        jsonify(
            {
                "status": "success",
                "message": "Two-factor authentication disabled. Please log in again.",
                "user": profile_schema.dump(user),
            }
        ),
        200,
    )
