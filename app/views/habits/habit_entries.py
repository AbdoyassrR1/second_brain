#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.habit import HabitEntry, HabitEntryStatus, Habit
from app.app import db, limiter

habit_entries = Blueprint("habit_entries", __name__)


@habit_entries.route("/<habit_id>", methods=["GET"])
@login_required
def get_habit_entries(habit_id):
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


@habit_entries.route("/add_entry/<habit_id>", methods=["POST"])
@limiter.limit("1 per day")
@login_required
def create_habit_entry(habit_id):
    data = request.form
    """
    Log a new entry for a habit by its id
    you can only log once per day
    """
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
    if not habit:
        abort(404, description="Habit not found or not owned by the current user")

    notes = data.get("notes", "")

    # Create a new habit entry 
    new_entry = HabitEntry(notes=notes)
    new_entry.habit_id = habit.id
    db.session.add(new_entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Habit entry added successfully",
        "entry": new_entry.to_dict()
    }), 201
