#!/usr/bin/python3
from app.app import create_app
from flask import jsonify

app = create_app()

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({
        "status": "error: Bad Request",
        "message": str(error.description)
        }), 400

@app.errorhandler(401)
def unauthorized_error(error):
    return jsonify({
        "status": "error: Unauthorized",
        "message": str(error.description)
        }), 401

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        "status": "error: Not Found",
        "message": str(error.description)
        }), 404

@app.errorhandler(409)
def conflict_error(error):
    return jsonify({
        "status": "error: Conflict",
        "message": str(error.description)
        }), 409

@app.errorhandler(429)
def ratelimit_error(error):
    return {
        "status": "error: Too Many Requests",
        "message": "You have exceeded the maximum number of requests allowed. Please try again later."
        }, 429

if __name__ == "__main__":
    app.run(host="localhost", debug=True)
