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
    query = Task.query.filter_by(user_id=current_user.id)

    # handle query parameters for filtering
    search = request.args.get("search")
    status = request.args.get("status")
    category = request.args.get("category")
    priority = request.args.get("priority")

    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))

    if status:
        try:
            status = TaskStatus[status.upper()]
            query = query.filter_by(status=status)
        except KeyError:
            abort(400, description="invalid status")

    if category:
        try:
            category = TaskCategory[category.upper()]
            query = query.filter_by(category=category)
        except KeyError:
            abort(400, description="invalid category")

    if priority:
        try:
            priority = TaskPriority[priority.upper()]
            query = query.filter_by(priority=priority)
        except KeyError:
            abort(400, description="invalid priority")

    # handle pagination
    page = request.args.get("page", default=1, type=int)
    per_page = request.args.get("per_page", default=10, type=int)
    paginated_tasks = query.paginate(page=page, per_page=per_page, error_out=False)

    # If no tasks were found
    if not paginated_tasks.items:
        abort(404, description="No Tasks Found")

    # Convert tasks to dictionary for the response
    tasks = [task.to_dict() for task in paginated_tasks.items]

    # Return the tasks with pagination metadata
    return jsonify({
        'tasks': tasks,
        'total_tasks': paginated_tasks.total,
        'total_pages': paginated_tasks.pages,
        'current_page': paginated_tasks.page,
        'next_page': paginated_tasks.next_num if paginated_tasks.has_next else None,
        'prev_page': paginated_tasks.prev_num if paginated_tasks.has_prev else None,
    })


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
