#!/usr/bin/env python3
"""
Database setup script for Lost and Found Portal
This script initializes the database tables and creates a default admin user.
"""

import os
import sys
from app import app, db
import models
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    """Initialize database tables and create default admin user"""
    try:
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully")
            
            logger.info("Creating default admin user...")
            admin = models.create_default_admin()
            if admin:
                logger.info("Default admin user created successfully")
                logger.info("Email: admin@example.com")
                logger.info("Password: admin123")
                logger.info("Please change these credentials after first login!")
            else:
                logger.info("Default admin user already exists")
            
            logger.info("Database setup completed successfully!")
            return True
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting database setup...")
    
    # Check if DATABASE_URL is set
    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL environment variable is not set.")
        logger.warning("Using SQLite database as fallback.")
    
    success = setup_database()
    
    if success:
        logger.info("Setup completed successfully!")
        sys.exit(0)
    else:
        logger.error("Setup failed!")
        sys.exit(1)