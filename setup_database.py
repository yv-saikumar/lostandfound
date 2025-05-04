#!/usr/bin/env python3
"""
Database setup script for Lost and Found Portal
This script initializes the database tables and creates a default admin user.
"""

import os
import sys
from app import app, db
from models import create_default_admin
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default admin account
        create_default_admin()

if __name__ == "__main__":
    setup_database()