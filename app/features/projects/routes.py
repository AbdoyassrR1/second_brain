#!/usr/bin/python3
"""Projects routes and endpoints."""

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.shared.decorators import require_json_body
from .service import ProjectService
from .schema import ProjectCreateSchema, ProjectUpdateSchema, ProjectResponseSchema

projects_bp = Blueprint("projects", __name__, url_prefix="/api/v1/projects")
project_service = ProjectService()
create_schema = ProjectCreateSchema()
update_schema = ProjectUpdateSchema()
response_schema = ProjectResponseSchema()


@projects_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit(lambda: current_app.config.get("PROJECT_RATE_LIMIT", "20 per minute"))
@require_json_body()
def create_project(json_data):
    """Create a new project."""
    user_id = get_jwt_identity()
    data = create_schema.load(json_data)
    project = project_service.create_project(user_id, **data)
    return jsonify({"status": "success", "project": response_schema.dump(project)}), 201


@projects_bp.route("", methods=["GET"])
@jwt_required()
def list_projects():
    """List projects for current user."""
    user_id = get_jwt_identity()
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    p = project_service.list_projects(user_id, page=page, per_page=per_page)
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


@projects_bp.route("/<project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id):
    """Get a specific project."""
    user_id = get_jwt_identity()
    project = project_service.get_project(project_id, user_id)
    return jsonify({"status": "success", "project": response_schema.dump(project)}), 200


@projects_bp.route("/<project_id>", methods=["PATCH"])
@jwt_required()
@require_json_body()
def update_project(project_id, json_data):
    """Update a project."""
    user_id = get_jwt_identity()
    data = update_schema.load(json_data)
    project = project_service.update_project(project_id, user_id, **data)
    return jsonify({"status": "success", "project": response_schema.dump(project)}), 200


@projects_bp.route("/<project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id):
    """Delete a project."""
    user_id = get_jwt_identity()
    project_service.delete_project(project_id, user_id)
    return jsonify({"status": "success", "message": "Project deleted"}), 200