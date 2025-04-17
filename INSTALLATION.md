# Installation Guide for Lost and Found Portal

Follow these steps to set up the Lost and Found Portal on your local machine or server.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- pip (Python package manager)

## Step 1: Clone the Repository

```bash
git clone <repository-url>
cd lost-and-found-portal
```

## Step 2: Set Up a Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

## Step 3: Install Dependencies

Install all the required packages:

```bash
pip install email-validator Flask Flask-Login Flask-Mail Flask-SQLAlchemy Flask-WTF gunicorn Pillow psycopg2-binary python-dotenv sendgrid SQLAlchemy twilio Werkzeug WTForms
```

## Step 4: Configure Environment Variables

Create a `.env` file in the project root directory with the following variables:

```
DATABASE_URL=postgresql://username:password@localhost:5432/lostandfound
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
SENDGRID_API_KEY=your_sendgrid_key (optional)
```

Replace the placeholders with your actual credentials.

## Step 5: Initialize the Database

First, ensure PostgreSQL is running and create a new database:

```sql
CREATE DATABASE lostandfound;
```

Then set up the database tables:

```bash
# Access Python shell
python

# In Python shell
from app import db, app
with app.app_context():
    db.create_all()
    exit()
```

## Step 6: Run the Application

```bash
# Development mode
flask run

# Production mode
gunicorn --bind 0.0.0.0:5000 main:app
```

The application should now be running at `http://localhost:5000`

## Step 7: Create an Admin User

After starting the application for the first time, a default admin user will be created:

- Email: admin@example.com
- Password: admin123

**Important:** Change these credentials immediately after your first login for security reasons.

## Troubleshooting

- **Database Connection Issues**: Verify your PostgreSQL connection string and ensure the database is running.
- **SMS Notification Issues**: Check your Twilio credentials and ensure your account has sufficient credit.
- **Email Notification Issues**: Verify your email server settings or SendGrid API key.

## Next Steps

- Customize the application settings in `app.py`
- Modify the templates in the `templates` directory to match your branding
- Add additional features as needed