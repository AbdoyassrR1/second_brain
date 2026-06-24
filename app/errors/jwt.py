#!/usr/bin/python3

from flask import jsonify, current_app, g, request
from flask_jwt_extended.exceptions import (
    NoAuthorizationError,
    InvalidHeaderError,
    JWTDecodeError,
    WrongTokenError,
    RevokedTokenError,
    FreshTokenRequired,
    UserClaimsVerificationError,
)
from .base import _error_response


def register_jwt_callbacks(jwt):
    """Register Flask-JWT-Extended callbacks for consistent JSON errors."""

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        """Return True when the token's jti is in the blocklist (logout / rotation)."""
        from app.features.auth.repository import TokenBlocklistRepository
        return TokenBlocklistRepository.is_revoked(jwt_payload["jti"])

    @jwt.unauthorized_loader
    def unauthorized_loader(reason):
        current_app.logger.warning(
            "Missing JWT",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "NoAuthorizationError",
                "error_message": reason,
            },
        )
        return _error_response(reason, "UNAUTHORIZED", 401)

    @jwt.invalid_token_loader
    def invalid_token_loader(reason):
        current_app.logger.warning(
            "Invalid JWT",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "JWTDecodeError",
                "error_message": reason,
            },
        )
        return _error_response(reason, "UNAUTHORIZED", 401)

    @jwt.expired_token_loader
    def expired_token_loader(jwt_header, jwt_payload):
        current_app.logger.warning(
            "Expired JWT",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "JWTDecodeError",
                "token_jti": jwt_payload.get("jti"),
                "token_sub": jwt_payload.get("sub"),
            },
        )
        return _error_response("Token has expired.", "UNAUTHORIZED", 401)

    @jwt.needs_fresh_token_loader
    def needs_fresh_token_loader(jwt_header, jwt_payload):
        current_app.logger.warning(
            "Fresh token required",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "FreshTokenRequired",
                "token_jti": jwt_payload.get("jti"),
                "token_sub": jwt_payload.get("sub"),
            },
        )
        return _error_response("Fresh authentication required.", "FRESH_TOKEN_REQUIRED", 401)

    @jwt.revoked_token_loader
    def revoked_token_loader(jwt_header, jwt_payload):
        current_app.logger.warning(
            "Revoked JWT",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "RevokedTokenError",
                "token_jti": jwt_payload.get("jti"),
                "token_sub": jwt_payload.get("sub"),
            },
        )
        return _error_response("Token has been revoked.", "UNAUTHORIZED", 401)

    @jwt.token_verification_failed_loader
    def token_verification_failed_loader(jwt_header, jwt_payload):
        current_app.logger.warning(
            "JWT claims verification failed",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "UserClaimsVerificationError",
                "token_jti": jwt_payload.get("jti"),
                "token_sub": jwt_payload.get("sub"),
            },
        )
        return _error_response("Access denied. Insufficient permissions.", "ACCESS_DENIED", 403)

    @jwt.user_lookup_error_loader
    def user_lookup_error_loader(jwt_header, jwt_payload):
        current_app.logger.warning(
            "JWT user lookup failed",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": "UserLookupError",
                "token_jti": jwt_payload.get("jti"),
                "token_sub": jwt_payload.get("sub"),
            },
        )
        return _error_response("User could not be loaded from token.", "UNAUTHORIZED", 401)

    return jwt


def register_jwt_error_handlers(app):
    @app.errorhandler(NoAuthorizationError)
    def jwt_no_authorization_error(error):
        current_app.logger.warning(
            "Missing or invalid JWT",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return _error_response(
            "Authentication credentials were not provided or are invalid.",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(InvalidHeaderError)
    def jwt_invalid_header_error(error):
        current_app.logger.warning(
            "Invalid JWT header format",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return _error_response(
            "Invalid authentication header format.",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(JWTDecodeError)
    def jwt_decode_error(error):
        current_app.logger.warning(
            "Invalid or expired JWT token",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return _error_response(
            "Token is invalid or has expired.",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(WrongTokenError)
    def jwt_wrong_token_error(error):
        current_app.logger.warning(
            "Wrong token type used",
            extra={
                "request_id": g.get("request_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return _error_response(
            "Wrong token type supplied for this endpoint.",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(RevokedTokenError)
    def jwt_revoked_token_error(error):
        current_app.logger.warning(
            "Revoked JWT token used",
            extra={
                "request_id": g.get("request_id"),
                "user_id": g.get("user_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
            }
        )
        return _error_response(
            "Token has been revoked.",
            "UNAUTHORIZED",
            401
        )

    @app.errorhandler(FreshTokenRequired)
    def jwt_fresh_token_required(error):
        current_app.logger.warning(
            "Fresh token required but not provided",
            extra={
                "request_id": g.get("request_id"),
                "user_id": g.get("user_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
            }
        )
        return _error_response(
            "Fresh authentication required. Please login again.",
            "FRESH_TOKEN_REQUIRED",
            401
        )

    @app.errorhandler(UserClaimsVerificationError)
    def jwt_user_claims_verification_error(error):
        current_app.logger.warning(
            "JWT claims verification failed",
            extra={
                "request_id": g.get("request_id"),
                "user_id": g.get("user_id"),
                "path": request.path,
                "method": request.method,
                "remote_addr": request.remote_addr,
                "exception_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        return _error_response(
            "Access denied. Insufficient permissions.",
            "ACCESS_DENIED",
            403
        )