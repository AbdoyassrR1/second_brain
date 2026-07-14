from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.shared.decorators import require_json_body
from .service import ReminderService
from .schema import ReminderSchema, ReminderUpdateSchema

reminders_bp = Blueprint("reminders", __name__, url_prefix="/api/v1/reminders")
reminder_service = ReminderService()
schema = ReminderSchema()
update_schema = ReminderUpdateSchema()


@reminders_bp.route("", methods=["POST"])
@jwt_required()
@require_json_body()
def create_reminder(json_data):
    user_id = get_jwt_identity()
    data = schema.load(json_data)
    reminder = reminder_service.create_reminder(data["task_id"], user_id, data["reminder_time"])
    return jsonify({"status": "success", "reminder": schema.dump(reminder)}), 201


@reminders_bp.route("", methods=["GET"])
@jwt_required()
def list_reminders():
    user_id = get_jwt_identity()
    status = request.args.get("status", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    p = reminder_service.list_reminders(user_id, status=status, page=page, per_page=per_page)

    return jsonify({
        "status": "success",
        "items": schema.dump(p.items, many=True),
        "total": p.total,
        "page": p.page,
        "per_page": p.per_page,
        "pages": p.pages,
        "next_page": p.next_num,
        "prev_page": p.prev_num,
    }), 200


@reminders_bp.route("/<reminder_id>", methods=["GET"])
@jwt_required()
def get_reminder(reminder_id):
    user_id = get_jwt_identity()
    reminder = reminder_service.get_reminder(reminder_id, user_id)
    return jsonify({"status": "success", "reminder": schema.dump(reminder)}), 200


@reminders_bp.route("/<reminder_id>", methods=["PATCH"])
@jwt_required()
@require_json_body()
def update_reminder(reminder_id, json_data):
    user_id = get_jwt_identity()
    data = update_schema.load(json_data)
    reminder = reminder_service.update_reminder(reminder_id, user_id, **data)
    return jsonify({"status": "success", "reminder": schema.dump(reminder)}), 200


@reminders_bp.route("/<reminder_id>", methods=["DELETE"])
@jwt_required()
def delete_reminder(reminder_id):
    user_id = get_jwt_identity()
    reminder_service.delete_reminder(reminder_id, user_id)
    return jsonify({"status": "success", "message": "Reminder deleted"}), 200
