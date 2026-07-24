#!/usr/bin/python3
"""Health/monitoring routes and endpoints."""

from flask import Blueprint, jsonify, current_app, request
from app.extensions import db
from datetime import datetime, UTC
from sqlalchemy import text
import threading

health_bp = Blueprint("health", __name__, url_prefix="/api/v1/monitor")
app_start_time = datetime.now(UTC)


def _run_with_timeout(fn, timeout=1.0):
    """Run a function with a timeout (seconds). Returns (ok, result_or_exception, elapsed_sec)."""
    result = {}

    def target():
        start = datetime.now(UTC)
        try:
            r = fn()
            result["ok"] = True
            result["value"] = r
        except Exception as e:
            result["ok"] = False
            result["value"] = e
        result["elapsed"] = (datetime.now(UTC) - start).total_seconds()

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout)
    if t.is_alive():
        return False, TimeoutError("timeout"), timeout
    return result.get("ok", False), result.get("value"), result.get("elapsed", 0)


@health_bp.route("/liveness", methods=["GET"])
def liveness_check():
    """Liveness: process is alive. Lightweight check."""
    return jsonify({"status": "alive", "timestamp": datetime.now(UTC).isoformat()}), 200


@health_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint with dependency verification and timings."""
    try:
        engine = db.engine

        def db_check():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True

        ok, val, elapsed = _run_with_timeout(db_check, timeout=1.0)

        uptime = (datetime.now(UTC) - app_start_time).total_seconds()
        payload = {
            "status": "ok" if ok else "degraded",
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": uptime,
            "dependencies": {
                "database": {
                    "ok": ok,
                    "latency_seconds": elapsed,
                    "detail": None if ok else str(val),
                }
            },
        }

        status_code = 200 if ok else 503
        return jsonify(payload), status_code
    except Exception:
        current_app.logger.exception("Health check failed")
        return (
            jsonify(
                {
                    "status": "error",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "message": "Service unavailable",
                }
            ),
            503,
        )


@health_bp.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness: strict dependency checks with short timeouts."""
    try:
        engine = db.engine

        def db_check():
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True

        ok, val, elapsed = _run_with_timeout(db_check, timeout=0.5)
        if ok:
            return jsonify({"status": "ready"}), 200
        else:
            current_app.logger.warning("Readiness dependency failed", extra={"detail": str(val)})
            return jsonify({"status": "not_ready", "reason": "Dependencies unavailable"}), 503
    except Exception:
        current_app.logger.exception("Readiness check failed")
        return jsonify({"status": "not_ready", "reason": "Exception during checks"}), 503
