#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Initialize the database
python setup_database.py

# Run database migrations
flask db upgrade