#!/usr/bin/python3
"""Labels routes and endpoints."""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.shared.decorators import require_json_body
from .service import LabelService
from .schema import LabelCreateSchema, LabelResponseSchema

labels_bp = Blueprint("labels", __name__, url_prefix="/api/v1/labels")
label_service = LabelService()
create_schema = LabelCreateSchema()
response_schema = LabelResponseSchema()


@labels_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("LABEL_RATE_LIMIT", "30 per minute"))
@require_json_body()
def create_label(json_data):
    """Create a new label."""
    user_id = get_jwt_identity()
    data = create_schema.load(json_data)
    label = label_service.create_label(user_id, **data)
    return jsonify({"status": "success", "label": response_schema.dump(label)}), 201


@labels_bp.route("", methods=["GET"])
@jwt_required()
def list_labels():
    """List labels for current user."""
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    p = label_service.list_labels(user_id, page=page, per_page=per_page)
    return jsonify({
        "status": "success",
        "items": response_schema.dump(p.items, many=True),
        "total": p.total,
        "page": p.page,
        "per_page": p.per_page,
        "pages": p.pages,
        "next_page": p.next_num,
        "prev_page": p.prev_num,
    }), 200


@labels_bp.route("/<label_id>", methods=["DELETE"])
@jwt_required()
def delete_label(label_id):
    """Delete a label."""
    user_id = get_jwt_identity()
    label_service.delete_label(label_id, user_id)
    return jsonify({"status": "success", "message": "Label deleted"}), 200