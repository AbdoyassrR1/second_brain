#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.task import Task, TaskCategory, TaskPriority, TaskStatus
from app.app import db


tasks = Blueprint("tasks", __name__)

@tasks.route("/", methods=["GET"], strict_slashes=False)
@login_required
def get_tasks():
    tasks = [task.to_dict() for task in current_user.tasks]
    return jsonify(tasks)


@tasks.route("/create_task", methods=["POST"])
@login_required
def create_task():
    data = request.form
    # check if the task exists for uniqueness
    if Task.query.filter_by(title=data["title"]).first():
        abort(409, description="this task already exists")

    # Check required fields
    required_fields = ["title", "status", "priority", "category"]
    for field in required_fields:
        if field not in data:
            abort(400, description=f"Missing {field}")

    # Validate and convert enum fields
    try:
        status = TaskStatus[data["status"].upper()]
        priority = TaskPriority[data["priority"].upper()]
        category = TaskCategory[data["category"].upper()]
    except KeyError as e:
        abort(400, description=f"Invalid value for {str(e)}")

    # Create new task
    new_task = Task(
        title=data["title"],
        description=data.get("description", ""),
        status=status,
        priority=priority,
        category=category
    )
    new_task.user_id = current_user.id
    db.session.add(new_task)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Task Created Successfully",
        "task": new_task.to_dict()
    }), 201
