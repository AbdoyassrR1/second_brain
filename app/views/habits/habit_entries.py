#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.habit import HabitEntry, HabitEntryStatus, Habit
from app.app import db, limiter, get_remote_address

habit_entries = Blueprint("habit_entries", __name__)

# Custom key function for rate-limiting based on habit and user
def habit_rate_limit_key():
    return f"{get_remote_address()}:{current_user.id}:{request.view_args['habit_id']}"


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
@limiter.limit("1 per day", key_func=habit_rate_limit_key)
@login_required
def create_habit_entry(habit_id):
    """ Log a new entry for a habit by its id, once per day """
    data = request.form
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
    }), 201


@habit_entries.route("/update_entry/<entry_id>", methods=["PATCH"])
@login_required
def update_habit_entry(entry_id):
    """Update an existing habit entry for the logged in user"""
    data = request.form

    # Fetch the entry by id 
    entry = HabitEntry.query.filter_by(id=entry_id).first()
    if not entry:
        abort(404, description="entry not found")

    # Fetch the habit by id 
    habit = entry.habit
    if not habit:
        abort(404, description="Habit not found")

    # Allowed fields to update
    allowed_fields = ["notes", "status"]
    is_updated = False

    # Validate and update the fields
    for key, value in data.items():
        if key in allowed_fields:

            if key == "notes" and value:
                entry.notes = value
                is_updated = True

            elif key == "status" and value:
                try:
                    entry.status = HabitEntryStatus[value.upper()]
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
        "message": "Habit entry updated successfully",
        "habit entry": entry.to_dict()
    }), 200


@habit_entries.route("/habit_stats/<habit_id>", methods=["GET"])
@login_required
def get_habit_stats(habit_id):
    """ get habit stats such as total entries completion rate """
    habit = Habit.query.filter_by(id=habit_id).first()
    if not habit:
        abort(404, description="Habit not found or not owned by the current User")
    entries = habit.entries

    # total entries
    total_entries = len(entries)

    # completed entries
    completed_entries = HabitEntry.query.filter_by(habit_id=habit_id, status=HabitEntryStatus.COMPLETED).all()

    # skipped entries
    completed_entries = HabitEntry.query.filter_by(habit_id=habit_id, status=HabitEntryStatus.SKIPPED).all()

    try:
        completion_rate = (len(completed_entries) / total_entries) * 100
    except ZeroDivisionError as a:
        abort(404, description=f"No Entries Found")

    return jsonify({
        "status": "success",
        "total entries": total_entries,
        "completion rate": f"%{completion_rate}"
    })
