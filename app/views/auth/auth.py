#!/usr/bin/python3
from flask import Blueprint, jsonify,  request, abort
from flask_login import login_user, logout_user, login_required
from app.app import db, limiter
from app.models.user import User

auth = Blueprint("auth", __name__)


# Registration route
@auth.route("/register", methods=["POST"])
@limiter.limit("5/minute")
def register():
    # get user data
    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    # check empty fields
    if not username or not email or not password:
        abort(400, description= "Please fill all fields")

    # check uniqness of the username and email
    if User.query.filter_by(username=username).first():
        abort(409, description="Username already exists")
    if User.query.filter_by(email=email).first():
        abort(409, description="Email already exists")

    # create a new user and add it to the data base
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    # log in the user
    login_user(new_user)

    return jsonify({
        "status": "success",
        "user": {
            "username": new_user.username,
            "email": new_user.email
        },
        "message": "User created and logged in"
    }), 201


# Login route
@auth.route("/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    # get user data
    email = request.form["email"]
    password = request.form["password"]
    remember_me = False 
    if "remember_me" in request.form:
        remember_me = request.form["remember_me"] 
    user = User.query.filter_by(email=email).first()

    if not user:
        abort(401, description="Invalid email")
    if not user.check_password(password):
        abort(401, description="Invalid password")

    login_user(user, remember=bool(remember_me))

    return jsonify({
        "status": "success",
        "user": {
            "username": user.username,
            "email": user.email
        },
        "message": "logged in"
    }), 200


# Logout route
@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return jsonify({
        "status": "success",
        "message": "User logged out"
        }), 200
