import os
import logging
from flask import Flask
from flask_mail import Mail
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    logger.info(f"Using database URL from environment: {database_url[:10]}...")
    # Add the following line to handle potential "postgres://" vs "postgresql://" issues
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    logger.warning("DATABASE_URL not found in environment, using SQLite as fallback")
    database_url = "sqlite:///lostandfound.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database with app
db.init_app(app)

# Configure Mail
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_USERNAME")
mail = Mail(app)

# Configure Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Import models after db is defined but before creating tables
import models

# Set up user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    try:
        # Try to convert to int for new DB IDs
        return models.User.query.get(int(user_id))
    except ValueError:
        # Handle old UUID strings by returning None - will require re-login
        logger.warning(f"Attempted to load user with non-integer ID: {user_id}")
        return None

# Create all tables and default admin user
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Create default admin user
        models.create_default_admin()
        logger.info("Default admin user created or verified")
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
