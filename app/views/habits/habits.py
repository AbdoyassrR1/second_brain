#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.habit import Habit, HabitStatus
from app.app import db

habits = Blueprint("habits", __name__)


@habits.route("/", methods=["GET"], strict_slashes=False)
@login_required
def get_habits():
    """ Get all habits related to the logged in User """
    query = Habit.query.filter_by(user_id=current_user.id)

    # handle query parameters for filtering
    search = request.args.get("search")
    status = request.args.get("status")

    if search:
        query = query.filter(Habit.title.ilike(f"%{search}%"))

    if status:
        try:
            status = HabitStatus[status.upper()]
            query = query.filter_by(status=status)
        except KeyError:
            abort(400, description="invalid status")

    habits = [habit.to_dict() for habit in query.order_by(Habit.created_at.desc()).all()]
    return jsonify(habits)


@habits.route("/create_habit", methods=["POST"])
@login_required
def create_habit():
    """Create a new habit for the logged in user"""
    data = request.form
    title = data["title"]
    description = data["description"]

    # check if the habit exists for the current user
    if Habit.query.filter_by(title=title, user_id=current_user.id).first():
        abort(409, description="this habit already exists for the current user")

    # Check required fields
    required_fields = ["title", "description"]
    for field in required_fields:
        if field not in data:
            abort(400, description=f"Missing {field}")
    if not title or not description:
        abort(400, description="please fill all fields")


    # Create new habit
    new_habit = Habit(
        title=title,
        description=description
    )
    new_habit.user_id = current_user.id
    db.session.add(new_habit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Habit Created Successfully",
        "habit": new_habit.to_dict()
    }), 201


@habits.route("/update_habit/<habit_id>", methods=["PATCH"])
@login_required
def update_habit(habit_id):
    """Update an existing habit for the logged in user"""
    data = request.form

    # Fetch the habit by id and make sure the user is the owner
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if not habit:
        abort(404, description="Habit not found or not owned by the current user")

    # Allowed fields to update
    allowed_fields = ["title", "description", "status"]
    is_updated = False

    # Validate and update the fields
    for key, value in data.items():
        if key in allowed_fields:

            if key == "title" and value:
                if Habit.query.filter_by(title=value, user_id=current_user.id).first():
                    abort(409, description="this habit already exists for the current user")
                habit.title = value
                is_updated = True

            elif key == "description" and value:
                habit.description = value
                is_updated = True

            elif key == "status" and value:
                try:
                    habit.status = HabitStatus[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid status value")

    # If no changes were made, return an error
    if not is_updated:
        abort(400, description="No valid fields to update or no changes made")

    # Commit the changes to the database
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Habit updated successfully",
        "habit": habit.to_dict()
    }), 200


@habits.route("/delete_habit/<habit_id>", methods=["DELETE"])
@login_required
def delete_habit(habit_id):
    """ delete habit for the logged in user """
    # Fetch the habit by id and make sure the user is the owner
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if not habit:
        abort(404, description="Habit not found or not owned by the current user")
    db.session.delete(habit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Habit deleted successfully"
    }), 200
