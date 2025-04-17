import os
import uuid
import datetime
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# In-memory storage
users = {}
items = {}
admin_users = {'admin@lostandfound.com'}  # Admin users by email

class User(UserMixin):
    def __init__(self, id, name, email, password, is_admin=False):
        self.id = id
        self.name = name
        self.email = email
        self.password_hash = generate_password_hash(password)
        self.is_admin = is_admin
        self.created_at = datetime.datetime.now()
        self.items_reported = []
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_admin': self.is_admin,
            'created_at': self.created_at,
            'items_reported': self.items_reported
        }
        
class Item:
    def __init__(self, id, item_type, title, description, category, date, location, 
                 contact_info, image_data, user_id, latitude=None, longitude=None):
        self.id = id
        self.item_type = item_type  # 'lost' or 'found'
        self.title = title
        self.description = description
        self.category = category
        self.date = date
        self.location = location
        self.latitude = latitude
        self.longitude = longitude
        self.contact_info = contact_info
        self.image_data = image_data  # Base64 encoded image
        self.user_id = user_id
        self.status = 'pending'  # 'pending', 'verified', 'claimed'
        self.created_at = datetime.datetime.now()
        self.claimed_by = None
        self.verified_by = None
        
    def to_dict(self):
        return {
            'id': self.id,
            'item_type': self.item_type,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'date': self.date,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'contact_info': self.contact_info,
            'image_data': self.image_data,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at,
            'claimed_by': self.claimed_by,
            'verified_by': self.verified_by
        }

def create_user(name, email, password, is_admin=False):
    user_id = str(uuid.uuid4())
    
    # Check if email already exists
    for user in users.values():
        if user.email == email:
            return None
    
    # Check if user should be an admin
    if email in admin_users:
        is_admin = True
    
    # Create the user
    user = User(user_id, name, email, password, is_admin)
    users[user_id] = user
    return user

def get_user_by_email(email):
    for user in users.values():
        if user.email == email:
            return user
    return None

def get_user_by_id(user_id):
    return users.get(user_id)

def load_user(user_id):
    return users.get(user_id)

def create_item(item_type, title, description, category, date, location, 
               contact_info, image_data, user_id, latitude=None, longitude=None):
    item_id = str(uuid.uuid4())
    item = Item(item_id, item_type, title, description, category, date, location, 
               contact_info, image_data, user_id, latitude, longitude)
    items[item_id] = item
    
    # Add item to user's reported items
    if user_id in users:
        users[user_id].items_reported.append(item_id)
    
    return item

def get_item_by_id(item_id):
    return items.get(item_id)

def get_all_items():
    return list(items.values())

def get_items_by_type(item_type):
    return [item for item in items.values() if item.item_type == item_type]

def get_items_by_user(user_id):
    return [item for item in items.values() if item.user_id == user_id]

def get_pending_items():
    return [item for item in items.values() if item.status == 'pending']

def update_item_status(item_id, status, admin_id=None):
    if item_id in items:
        items[item_id].status = status
        if status == 'verified' and admin_id:
            items[item_id].verified_by = admin_id
        return True
    return False

def claim_item(item_id, user_id):
    if item_id in items:
        items[item_id].status = 'claimed'
        items[item_id].claimed_by = user_id
        return True
    return False

def search_items(query, category=None, item_type=None, status=None):
    results = []
    for item in items.values():
        # Apply filters
        if category and item.category != category:
            continue
        if item_type and item.item_type != item_type:
            continue
        if status and item.status != status:
            continue
            
        # Search in title and description
        if (query.lower() in item.title.lower() or 
            query.lower() in item.description.lower() or
            query.lower() in item.location.lower()):
            results.append(item)
    
    return results

# Create an admin user if not exists (only in development)
if 'admin@lostandfound.com' not in [u.email for u in users.values()]:
    create_user("Admin", "admin@lostandfound.com", "admin123", is_admin=True)
