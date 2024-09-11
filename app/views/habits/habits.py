#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.habit import Habit, HabitEntry, HabitStatus
from app.app import db

habits = Blueprint("habits", __name__)


@habits.route("/", methods=["GET"], strict_slashes=False)
@login_required
def get_habits():
    """ Get all habits related to the logged in User """
    habits = [habit.to_dict() for habit in current_user.habits]
    return jsonify(habits)


@habits.route("/create_habit", methods=["POST"])
@login_required
def create_task():
    """Create a new habit for the logged in user"""
    data = request.form
    # check if the habit exists for the current user
    if Habit.query.filter_by(title=data["title"], user_id=current_user.id).first():
        abort(409, description="this habit already exists for the current user")

    # Check required fields
    required_fields = ["title"]
    for field in required_fields:
        if field not in data:
            abort(400, description=f"Missing {field}")


    # Create new habit
    new_habit = Habit(
        title=data["title"],
        description=data.get("description", ""),
    )
    new_habit.user_id = current_user.id
    db.session.add(new_habit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Habit Created Successfully",
        "habit": new_habit.to_dict()
    }), 201
