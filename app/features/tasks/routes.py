#!/usr/bin/python3
"""Tasks routes and endpoints."""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.shared.decorators import require_json_body
from app.shared.exceptions import ValidationError
from .service import TaskService
from .schema import (
    TaskCreateSchema, TaskUpdateSchema, TaskResponseSchema,
    BulkTaskActionSchema, StatisticsResponseSchema,
)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")
task_service = TaskService()
create_schema = TaskCreateSchema()
update_schema = TaskUpdateSchema()
response_schema = TaskResponseSchema()
bulk_action_schema = BulkTaskActionSchema()
statistics_schema = StatisticsResponseSchema()


@tasks_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TASK_RATE_LIMIT", "10 per minute"))
@require_json_body()
def create_task(json_data):
    """Create a new task."""
    user_id = get_jwt_identity()
    data = create_schema.load(json_data)
    task = task_service.create_task(user_id, **data)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 201


@tasks_bp.route("", methods=["GET"])
@jwt_required()
def list_tasks():
    """List tasks for current user with advanced filtering, sorting, and pagination."""
    user_id = get_jwt_identity()
    status = request.args.get("status")
    priority = request.args.get("priority")
    project_id = request.args.get("project_id")
    parent_task_id = request.args.get("parent_task_id")
    due = request.args.get("due")
    overdue = request.args.get("overdue")
    q = request.args.get("q")
    labels = request.args.get("labels")
    include_archived = request.args.get("include_archived", "false").lower() == "true"
    archived = request.args.get("archived")
    sort = request.args.get("sort")
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    tasks, total = task_service.list_tasks(
        user_id,
        status=status,
        priority=priority,
        project_id=project_id,
        parent_task_id=parent_task_id,
        due=due,
        overdue=overdue,
        q=q,
        labels=labels,
        include_archived=include_archived,
        archived=archived,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return jsonify({
        "status": "success",
        "items": response_schema.dump(tasks, many=True),
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }), 200


@tasks_bp.route("/statistics", methods=["GET"])
@jwt_required()
def get_statistics():
    """Get task statistics for the current user."""
    user_id = get_jwt_identity()
    stats = task_service.get_statistics(user_id)
    return jsonify({
        "status": "success",
        "statistics": stats,
    }), 200


@tasks_bp.route("/<task_id>", methods=["GET"])
@jwt_required()
def get_task(task_id):
    """Get a specific task."""
    user_id = get_jwt_identity()
    task = task_service.get_task(task_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>", methods=["PATCH"])
@jwt_required()
@require_json_body()
def update_task(task_id, json_data):
    """Update a task."""
    user_id = get_jwt_identity()
    data = update_schema.load(json_data)
    task = task_service.update_task(task_id, user_id, **data)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    """Soft delete a task."""
    user_id = get_jwt_identity()
    task_service.delete_task(task_id, user_id)
    return jsonify({"status": "success", "message": "Task deleted"}), 200


@tasks_bp.route("/<task_id>/restore", methods=["POST"])
@jwt_required()
def restore_task(task_id):
    """Restore a soft-deleted task."""
    user_id = get_jwt_identity()
    task = task_service.restore_task(task_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>/complete", methods=["POST"])
@jwt_required()
def complete_task(task_id):
    """Mark a task as completed."""
    user_id = get_jwt_identity()
    task = task_service.mark_completed(task_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>/archive", methods=["POST"])
@jwt_required()
def archive_task(task_id):
    """Archive a task."""
    user_id = get_jwt_identity()
    task = task_service.archive_task(task_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>/restore-archive", methods=["POST"])
@jwt_required()
def restore_archive_task(task_id):
    """Restore a task from archive."""
    user_id = get_jwt_identity()
    task = task_service.restore_archive_task(task_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>/subtasks", methods=["GET"])
@jwt_required()
def get_subtasks(task_id):
    """Get subtasks for a task."""
    user_id = get_jwt_identity()
    subtasks = task_service.get_subtasks(task_id, user_id)
    return jsonify({
        "status": "success",
        "items": response_schema.dump(subtasks, many=True),
        "count": len(subtasks),
    }), 200


@tasks_bp.route("/<task_id>/labels", methods=["POST"])
@jwt_required()
@require_json_body()
def assign_label_to_task(task_id, json_data):
    """Assign a label to a task."""
    user_id = get_jwt_identity()
    label_id = json_data.get("label_id")
    if not label_id:
        raise ValidationError("label_id is required")
    from app.features.labels.service import LabelService
    label_service = LabelService()
    task = label_service.assign_label_to_task(task_id, label_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


@tasks_bp.route("/<task_id>/labels/<label_id>", methods=["DELETE"])
@jwt_required()
def remove_label_from_task(task_id, label_id):
    """Remove a label from a task."""
    user_id = get_jwt_identity()
    from app.features.labels.service import LabelService
    label_service = LabelService()
    task = label_service.remove_label_from_task(task_id, label_id, user_id)
    return jsonify({"status": "success", "task": response_schema.dump(task)}), 200


# ── Bulk Operations ────────────────────────────────────────────────────


@tasks_bp.route("/bulk", methods=["PATCH"])
@jwt_required()
@require_json_body()
def bulk_update_tasks(json_data):
    """Bulk update tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    task_ids = data["task_ids"]

    # Determine the operation based on request body
    updates = {k: v for k, v in json_data.items() if k != "task_ids"}

    if not updates:
        raise ValidationError("No update fields provided")

    tasks = task_service.bulk_update(task_ids, user_id, **updates)
    return jsonify({
        "status": "success",
        "message": f"Updated {len(tasks)} task(s)",
        "tasks": response_schema.dump(tasks, many=True),
    }), 200


@tasks_bp.route("/bulk", methods=["DELETE"])
@jwt_required()
@require_json_body()
def bulk_delete_tasks(json_data):
    """Bulk soft delete tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    tasks = task_service.bulk_soft_delete(data["task_ids"], user_id)
    return jsonify({
        "status": "success",
        "message": f"Deleted {len(tasks)} task(s)",
    }), 200


@tasks_bp.route("/bulk/complete", methods=["POST"])
@jwt_required()
@require_json_body()
def bulk_complete_tasks(json_data):
    """Bulk complete tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    tasks = task_service.bulk_complete(data["task_ids"], user_id)
    return jsonify({
        "status": "success",
        "message": f"Completed {len(tasks)} task(s)",
        "tasks": response_schema.dump(tasks, many=True),
    }), 200


@tasks_bp.route("/bulk/archive", methods=["POST"])
@jwt_required()
@require_json_body()
def bulk_archive_tasks(json_data):
    """Bulk archive tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    tasks = task_service.bulk_archive(data["task_ids"], user_id)
    return jsonify({
        "status": "success",
        "message": f"Archived {len(tasks)} task(s)",
    }), 200


@tasks_bp.route("/bulk/restore-archive", methods=["POST"])
@jwt_required()
@require_json_body()
def bulk_restore_archive_tasks(json_data):
    """Bulk restore archived tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    tasks = task_service.bulk_restore_archive(data["task_ids"], user_id)
    return jsonify({
        "status": "success",
        "message": f"Restored {len(tasks)} task(s) from archive",
    }), 200


@tasks_bp.route("/bulk/restore", methods=["POST"])
@jwt_required()
@require_json_body()
def bulk_restore_tasks(json_data):
    """Bulk restore soft-deleted tasks."""
    user_id = get_jwt_identity()
    data = bulk_action_schema.load(json_data)
    tasks = task_service.bulk_restore(data["task_ids"], user_id)
    return jsonify({
        "status": "success",
        "message": f"Restored {len(tasks)} task(s)",
    }), 200


@tasks_bp.route("/bulk/labels", methods=["POST"])
@jwt_required()
@require_json_body()
def bulk_assign_labels(json_data):
    """Bulk assign labels to tasks."""
    user_id = get_jwt_identity()
    task_ids = json_data.get("task_ids", [])
    label_id = json_data.get("label_id")
    action = json_data.get("action", "assign")  # "assign" or "remove"

    if not task_ids or not label_id:
        raise ValidationError("task_ids and label_id are required")

    from app.features.labels.service import LabelService
    label_service = LabelService()

    results = []
    for task_id in task_ids:
        try:
            if action == "assign":
                task = label_service.assign_label_to_task(task_id, label_id, user_id)
            else:
                task = label_service.remove_label_from_task(task_id, label_id, user_id)
            results.append(task)
        except Exception:
            continue

    return jsonify({
        "status": "success",
        "message": f"Processed {len(results)} task(s)",
    }), 200