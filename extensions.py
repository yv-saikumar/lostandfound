from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase

# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# Initialize extensions without binding them to the app yet
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# Configure Login Manager defaults
login_manager.login_view = "login"
login_manager.login_message_category = "info"