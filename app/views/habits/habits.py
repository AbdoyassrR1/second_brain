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
