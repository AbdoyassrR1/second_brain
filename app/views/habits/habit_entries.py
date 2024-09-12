#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.habit import HabitEntry, HabitEntryStatus, Habit 
from app.app import db

habit_entries = Blueprint("habit_entries", __name__)


@habit_entries.route("/<habit_id>", methods=["GET"])
@login_required
def habit_history(habit_id):
    """Get a list of all entries for a certain habit by its id"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if not habit:
        abort(404, description="Habit not found or not owned by the current user")
    print("debugging")

    # Get all entries for the habit
    entries = HabitEntry.query.filter_by(habit_id=habit.id).order_by(HabitEntry.created_at.desc()).all()


    # Convert to dictionary for JSON response
    habit_history = [entry.to_dict() for entry in entries]

    return jsonify({
        "habit": habit.title,
        "entries": habit_history
    })
