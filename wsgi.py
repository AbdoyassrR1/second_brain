#!/usr/bin/python3
"""WSGI entry point for production servers (Gunicorn, uWSGI, etc.)."""

import os
from app import create_app

config_name = os.getenv("FLASK_ENV", "production")
app = create_app(config_name)

if __name__ == "__main__":
    app.run()
