#!/usr/bin/python3
from flask import Blueprint, request, jsonify
from app.models.user import User
from flask_login import logout_user, login_required, current_user

profile = Blueprint("profile", __name__)


# Protected profile route
@profile.route("/profile")
@login_required
def profile():
    return jsonify({"username": current_user.username,
                    "email": current_user.email}), 200
