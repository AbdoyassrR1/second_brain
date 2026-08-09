#!/usr/bin/python3
"""Time tracking routes and endpoints."""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.shared.decorators import require_json_body
from .service import TimeTrackingService
from .schema import (
    TimerStartSchema,
    TimerAddTasksSchema,
    TimeEntryCreateSchema,
    TimeEntryUpdateSchema,
    TimeEntryListQuerySchema,
    ReportQuerySchema,
    TimeEntryResponseSchema,
    ReportResponseSchema,
)

time_tracking_bp = Blueprint("time_tracking", __name__, url_prefix="/api/v1/time")
service = TimeTrackingService()
timer_start_schema = TimerStartSchema()
timer_add_tasks_schema = TimerAddTasksSchema()
entry_create_schema = TimeEntryCreateSchema()
entry_update_schema = TimeEntryUpdateSchema()
entry_list_query_schema = TimeEntryListQuerySchema()
report_query_schema = ReportQuerySchema()
entry_response_schema = TimeEntryResponseSchema()
report_response_schema = ReportResponseSchema()


# ── Timer ───────────────────────────────────────────────────────────────


@time_tracking_bp.route("/timer/start", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
@require_json_body()
def start_timer(json_data):
    """Start a running timer linked to one or more tasks."""
    user_id = get_jwt_identity()
    data = timer_start_schema.load(json_data)
    entry = service.start_timer(
        user_id, data["task_ids"], note=data.get("note")
    )
    return jsonify({"status": "success", "timer": entry_response_schema.dump(entry)}), 201


@time_tracking_bp.route("/timer/current", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_READ_RATE_LIMIT", "60 per minute"))
def get_current_timer():
    """Get the user's running timer (or null)."""
    user_id = get_jwt_identity()
    entry = service.get_current_timer(user_id)
    return jsonify({
        "status": "success",
        "timer": entry_response_schema.dump(entry) if entry else None,
    }), 200


@time_tracking_bp.route("/timer/tasks", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
@require_json_body()
def add_tasks_to_timer(json_data):
    """Add tasks to the running timer (already-linked ids are skipped)."""
    user_id = get_jwt_identity()
    data = timer_add_tasks_schema.load(json_data)
    entry, added, skipped = service.add_tasks_to_timer(user_id, data["task_ids"])
    return jsonify({
        "status": "success",
        "timer": entry_response_schema.dump(entry),
        "added": added,
        "skipped": skipped,
    }), 200


@time_tracking_bp.route("/timer/tasks/<task_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
def remove_task_from_timer(task_id):
    """Remove a task from the running timer."""
    user_id = get_jwt_identity()
    entry = service.remove_task_from_timer(user_id, task_id)
    return jsonify({"status": "success", "timer": entry_response_schema.dump(entry)}), 200


@time_tracking_bp.route("/timer/stop", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
def stop_timer():
    """Stop the running timer and split the elapsed time across its tasks."""
    user_id = get_jwt_identity()
    entry = service.stop_timer(user_id)
    return jsonify({"status": "success", "timer": entry_response_schema.dump(entry)}), 200


# ── Manual entries ──────────────────────────────────────────────────────


@time_tracking_bp.route("/entries", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
@require_json_body()
def create_entry(json_data):
    """Create a completed (manual) time entry."""
    user_id = get_jwt_identity()
    data = entry_create_schema.load(json_data)
    entry = service.create_entry(
        user_id,
        data["task_ids"],
        data["started_at"],
        data["ended_at"],
        note=data.get("note"),
    )
    return jsonify({"status": "success", "entry": entry_response_schema.dump(entry)}), 201


@time_tracking_bp.route("/entries", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_READ_RATE_LIMIT", "60 per minute"))
def list_entries():
    """List time entries with filters and pagination."""
    user_id = get_jwt_identity()
    query_data = entry_list_query_schema.load(request.args.to_dict())
    p = service.list_entries(
        user_id,
        from_dt=query_data.get("from_"),
        to_dt=query_data.get("to_"),
        task_id=query_data.get("task_id"),
        running=query_data.get("running"),
        page=query_data["page"],
        per_page=query_data["per_page"],
    )
    return jsonify({
        "status": "success",
        "items": entry_response_schema.dump(p.items, many=True),
        "total": p.total,
        "page": p.page,
        "per_page": p.per_page,
        "pages": p.pages,
        "next_page": p.next_num,
        "prev_page": p.prev_num,
    }), 200


@time_tracking_bp.route("/entries/<entry_id>", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_READ_RATE_LIMIT", "60 per minute"))
def get_entry(entry_id):
    """Get a single time entry."""
    user_id = get_jwt_identity()
    entry = service.get_entry(entry_id, user_id)
    return jsonify({"status": "success", "entry": entry_response_schema.dump(entry)}), 200


@time_tracking_bp.route("/entries/<entry_id>", methods=["PATCH"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
@require_json_body()
def update_entry(entry_id, json_data):
    """Update a time entry (note / time range / task ids)."""
    user_id = get_jwt_identity()
    data = entry_update_schema.load(json_data)
    entry = service.update_entry(entry_id, user_id, data)
    return jsonify({"status": "success", "entry": entry_response_schema.dump(entry)}), 200


@time_tracking_bp.route("/entries/<entry_id>", methods=["DELETE"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("TIME_RATE_LIMIT", "30 per minute"))
def delete_entry(entry_id):
    """Hard-delete a completed time entry."""
    user_id = get_jwt_identity()
    service.delete_entry(entry_id, user_id)
    return jsonify({"status": "success", "message": "Time entry deleted"}), 200


# ── Reports ─────────────────────────────────────────────────────────────


@time_tracking_bp.route("/reports", methods=["GET"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("REPORT_RATE_LIMIT", "10 per minute"))
def get_report():
    """Aggregate completed time entries into a time / task / project report."""
    user_id = get_jwt_identity()
    query_data = report_query_schema.load(request.args.to_dict())
    report = service.generate_report(
        user_id,
        query_data["group_by"],
        query_data["from_"],
        query_data["to_"],
        tz=query_data.get("tz", "UTC"),
    )
    return jsonify({
        "status": "success",
        "report": report_response_schema.dump(report),
    }), 200
