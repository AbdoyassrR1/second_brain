#!/usr/bin/python3
from flask import Blueprint, request, jsonify, abort
from flask_login import logout_user, login_required, current_user
from app.models.user import User
from app.app import db, bcrypt


profile = Blueprint("profile", __name__)


# Protected profile route
@profile.route("/", strict_slashes=False)
@login_required
def get_profile():
    return jsonify(current_user.to_dict()), 200


# Protected profile update route
@profile.route("/update_profile", methods=["PATCH"])
@login_required
def update_profile():
    updated_data = request.form
    allowed_fields = ["username", "password"]

    for key, value in updated_data.items():
        if key in allowed_fields:
            if key == "username":
                # check if this username already exists
                if User.query.filter_by(username=updated_data[key]).first():
                    abort(409, description="Username already exists")
                # check the length of the username
                if len(updated_data[key]) < 4:
                    abort(400, description="Username must be at least 4 Chars")
                setattr(current_user, key, value)
                db.session.commit()
            elif key == "password":
                # check the old password
                old_password = updated_data["old password"]
                if not current_user.check_password(old_password):
                    abort(401, description="Incorrect old password")
                else:
                    new_password = updated_data[key]
                    current_user.set_password(new_password)
                    db.session.commit()


    return jsonify({
        "status": "success",
        "message": "User Date has been updated"
    })
