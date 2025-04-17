# Lost and Found Portal

A comprehensive web application for reporting and retrieving lost and found items, built using Flask and PostgreSQL.

## Features

- **User Management**: Registration, login, profiles with images
- **Item Management**: Report lost/found items with details and images
- **Search & Matching**: Find items by various criteria
- **Notifications**: Email and SMS notifications via Twilio
- **Messaging System**: Internal communication between users
- **Admin Panel**: Verify items, manage users, view statistics
- **Responsive Design**: Mobile-friendly interface

## Installation

For detailed installation instructions, please see [INSTALLATION.md](INSTALLATION.md)

1. Clone the repository
2. Set up a virtual environment (recommended)
3. Install dependencies as listed in pyproject.toml
4. Configure environment variables (see below)
5. Initialize the database
6. Run the application:
   ```
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

## Environment Variables

Create a `.env` file with the following variables:

```
DATABASE_URL=postgresql://username:password@localhost:5432/lostandfound
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_phone
SENDGRID_API_KEY=your_sendgrid_key (optional)
```

## Project Structure

- `app.py`: Main application setup with database initialization
- `main.py`: Entry point for the application
- `models.py`: Database models (User, Item, Message, Proof)
- `forms.py`: Form definitions for all user inputs
- `routes.py`: URL routes and view functions
- `utils.py`: Utility functions for image processing and notifications
- `sms.py`: SMS notification functions using Twilio
- `templates/`: HTML templates (base, admin, user interfaces)
- `static/`: CSS, JavaScript, and map integration

### Key Templates
- `base.html`: Main layout template
- `admin_*.html`: Admin interface templates
- `item_details.html`: Detailed view of lost/found items
- `messages.html`: User messaging interface
- `profile.html`: User profile management

## Default Admin Account

Username: admin@example.com
Password: admin123

*Change these credentials immediately after first login.*

## Key Functionality

### For Users
- Register and login with email verification
- Report lost or found items with descriptions and images
- Search for items by category, location, and keywords
- Receive notifications when matching items are found
- Claim items and provide proof of ownership
- Communicate with other users through the messaging system
- Update profile information and notification preferences

### For Administrators
- Verify reported items
- Manage user accounts and permissions
- View system statistics and activity
- Monitor and moderate item claims

## Technologies Used

- **Backend**: Python, Flask, SQLAlchemy
- **Database**: PostgreSQL
- **Frontend**: HTML, CSS, JavaScript
- **Notifications**: Twilio (SMS), Email
- **Deployment**: Compatible with various hosting platforms

## SAI Motto

The Lost and Found Portal follows the "SAI" motto:
- **Secure**: Data protection and secure user authentication
- **Assist**: Helping users find their lost items or return found belongings
- **Inform**: Keeping users informed through notifications and updates

## License

This project is available for personal and commercial use. Please refer to the license file for details.