import os
import logging
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from extensions import db, mail, login_manager
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.INFO if os.environ.get('RENDER') else logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
# Enable production mode if running on Render
app.config['ENV'] = 'production' if os.environ.get('RENDER') else 'development'
app.config['DEBUG'] = not os.environ.get('RENDER')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure maximum file upload size (25MB)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure instance directory exists
os.makedirs(app.instance_path, exist_ok=True)

# Configure database
database_url = os.environ.get("DATABASE_URL")
if database_url:
    logger.info(f"Using database URL from environment: {database_url[:10]}...")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
else:
    logger.warning("DATABASE_URL not found in environment, using SQLite as fallback")
    database_url = "sqlite:///" + os.path.join(app.instance_path, "lostandfound.db")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure email
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")

# Initialize extensions
db.init_app(app)
mail.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Add custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(s):
    if not s:
        return ""
    return s.replace('\n', '<br>')

# Initialize migrations
migrate = Migrate(app, db)

# Initialize CSRF protection
csrf = CSRFProtect()
csrf.init_app(app)

# Import models at the start to avoid circular imports
from models import User

# Configure user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import remaining models and create tables
with app.app_context():
    from models import Item, Message, Proof, create_default_admin
    db.create_all()
    create_default_admin()

# Set up scheduler for periodic tasks
scheduler = BackgroundScheduler()
scheduler.start()

def run_archive_task():
    with app.app_context():
        from models import archive_expired_items
        num_archived = archive_expired_items()
        if num_archived > 0:
            logger.info(f"Archived {num_archived} expired items")

# Run archive task every day at midnight
scheduler.add_job(run_archive_task, 'cron', hour=0, minute=0)

# Import routes after app creation to avoid circular imports
from routes import *

if __name__ == "__main__":
    app.run(debug=True)
