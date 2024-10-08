#!/usr/bin/python3
from flask import Blueprint, request, jsonify, abort
from flask_login import logout_user, login_required, current_user
from app.models.user import User
from app.app import db
from flasgger.utils import swag_from


profile = Blueprint("profile", __name__)


# Protected profile route
@profile.route("/", strict_slashes=False)
@login_required
@swag_from("../docs/auth/get_profile.yml")
def get_profile():
    """ get the logged in user profile """
    return jsonify(current_user.to_dict()), 200


# Protected profile update route
@profile.route("/update_profile", methods=["PATCH"])
@login_required
@swag_from("../docs/auth/update_profile.yml")
def update_profile():
    """ Update the logged in user data """
    updated_data = request.form
    allowed_fields = ["username", "password"]
    is_updated = False

    for key, value in updated_data.items():
        if key in allowed_fields:
            if key == "username":
                # Check if the username is not empty
                if not value:
                    abort(400, description="Username cannot be empty")
                # check the length of the username
                if len(value) < 4:
                    abort(400, description="Username must be at least 4 Chars")
                # check if this username already exists
                if User.query.filter_by(username=value).first():
                    abort(409, description="Username already exists")
                setattr(current_user, key, value)
                is_updated = True

            elif key == "password":
                if "old_password" not in updated_data:
                    abort(400, description="Missing old password")
                new_password = value
                old_password = updated_data["old_password"]
                # # Check if the password and old password are not empty
                if not old_password or not new_password:
                    abort(400, description="Both old and new passwords must be provided")
                # check the old password
                if not current_user.check_password(old_password):
                    abort(401, description="Incorrect old password")

                current_user.set_password(new_password)
                is_updated = True
                logout_user()

    if not is_updated:
        return jsonify({
            "status": "error",
            "message": "No Changes Made"
        }), 400

    # Commit the changes to the database
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Profile Updated Successfully"
    }), 200


@profile.route("/delete_account", methods=["DELETE"])
@login_required
@swag_from("../docs/auth/delete_account.yml")
def delete_account():
    """ Delete the logged in user account """
    password = request.form.get("password")

    # confirm password before deletion for more security
    if not password:
        abort(400, description="Confirming the Password is Required")
    if not current_user.check_password(password):
        abort(400, description="Incorrect password")

    db.session.delete(current_user)
    db.session.commit()
    logout_user()

    return jsonify({
        "status": "success",
        "message": "User Account Deleted Successfully"
    }), 200
