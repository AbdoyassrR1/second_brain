#!/usr/bin/python3
from flask import Blueprint, request, abort, jsonify
from flask_login import current_user, login_required
from app.models.task import Task, TaskCategory, TaskPriority, TaskStatus
from app.app import db


tasks = Blueprint("tasks", __name__)

@tasks.route("/", methods=["GET"], strict_slashes=False)
@login_required
def get_tasks():
    """get all tasks related to the logged in user"""
    tasks = [task.to_dict() for task in current_user.tasks]
    return jsonify(tasks)


@tasks.route("/create_task", methods=["POST"])
@login_required
def create_task():
    """Create a new task for the logged in user"""
    data = request.form
    # check if the task exists for the current user
    if Task.query.filter_by(title=data["title"], user_id=current_user.id).first():
        abort(409, description="this task already exists for the current user")

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
        error = str(e).split("\'")[1]
        abort(400, description=f"Invalid value for {error}")

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


@tasks.route("/update_task/<task_id>", methods=["PATCH"])
@login_required
def update_task(task_id):
    """Update an existing task for the logged in user"""
    data = request.form

    # Fetch the task by id and make sure the user is the owner
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        abort(404, description="Task not found or not owned by the current user")

    # Allowed fields to update
    allowed_fields = ["title", "description", "status", "priority", "category"]
    is_updated = False

    # Validate and update the fields
    for key, value in data.items():
        if key in allowed_fields:

            if key == "title" and value:
                if Task.query.filter_by(title=value, user_id=current_user.id).first():
                    abort(409, description="this task already exists for the current user")
                task.title = value
                is_updated = True

            # update the description even if the value if empty
            elif key == "description":
                task.description = value
                is_updated = True

            elif key == "status" and value:
                try:
                    task.status = TaskStatus[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid status value")
            
            elif key == "priority" and value:
                try:
                    task.priority = TaskPriority[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid priority value")
            
            elif key == "category" and value:
                try:
                    task.category = TaskCategory[value.upper()]
                    is_updated = True
                except KeyError:
                    abort(400, description="Invalid category value")

    # If no changes were made, return an error
    if not is_updated:
        return jsonify({
            "status": "error",
            "message": "No valid fields to update or no changes made"
        }), 400

    # Commit the changes to the database
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Task updated successfully",
        "task": task.to_dict()
    }), 200


@tasks.route("/delete_task/<task_id>", methods=["DELETE"])
@login_required
def delete_task(task_id):
    """ delete task for the logged in user """
    # Fetch the task by id and make sure the user is the owner
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first()
    if not task:
        abort(404, description="Task not found or not owned by the current user")
    db.session.delete(task)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Task deleted successfully"
    }), 200
