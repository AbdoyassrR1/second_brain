#!/usr/bin/python3
from app.app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host="localhost", debug=True)
