#!/bin/bash

# Navigate to the app directory
cd app/

# Initialize the database (only needed the first time)
flask db init

# Generate the migration script
flask db migrate

# Apply the migration to the database
flask db upgrade

# Navigate back to the root directory
cd ..

# Run the Flask app
python3 run.py
