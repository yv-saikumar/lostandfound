import os
import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Text, ForeignKey, DateTime, String, Boolean, Float, Integer
from sqlalchemy.orm import relationship
from extensions import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    profile_picture = db.Column(db.Text, nullable=True)  # Base64 encoded image
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Notifications preferences
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    
    # Relationships
    items = relationship("Item", back_populates="owner", foreign_keys="Item.user_id")
    claimed_items = relationship("Item", back_populates="claimer", foreign_keys="Item.claimed_by")
    verified_items = relationship("Item", back_populates="verifier", foreign_keys="Item.verified_by")
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="recipient", foreign_keys="Message.recipient_id")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'profile_picture': self.profile_picture,
            'is_admin': self.is_admin,
            'created_at': self.created_at
        }

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_active': self.is_active,
            'created_at': self.created_at
        }

# Add other_category field to Item model
class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    item_type = db.Column(db.String(10), nullable=False)  # 'lost' or 'found'
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)  # New: Auto-archive date
    location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    contact_info = db.Column(db.String(100), nullable=False)
    images = db.Column(db.JSON, nullable=True)  # New: Multiple images as JSON array
    tags = db.Column(db.JSON, nullable=True)  # New: Auto-generated tags
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'verified', 'claimed', 'archived'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    claimed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    archived_at = db.Column(db.DateTime, nullable=True)  # New: Archive timestamp
    other_category = db.Column(db.String(50), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="items", foreign_keys=[user_id])
    claimer = relationship("User", back_populates="claimed_items", foreign_keys=[claimed_by])
    verifier = relationship("User", back_populates="verified_items", foreign_keys=[verified_by])
    proofs = relationship("Proof", back_populates="item", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'item_type': self.item_type,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'date': self.date,
            'expiry_date': self.expiry_date,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'contact_info': self.contact_info,
            'images': self.images,
            'tags': self.tags,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at,
            'claimed_by': self.claimed_by,
            'verified_by': self.verified_by,
            'archived_at': self.archived_at
        }

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image = db.Column(db.Text, nullable=True)  # Base64 encoded image
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'), nullable=True)
    
    # Relationships
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_id])
    replies = relationship("Message", backref=db.backref("parent", remote_side=[id]))

class Proof(db.Model):
    __tablename__ = 'proofs'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.Text, nullable=True)  # Base64 encoded image or document
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    claimed_at = db.Column(db.DateTime, nullable=True)  # When the claim was approved
    rejected_at = db.Column(db.DateTime, nullable=True)  # When the claim was rejected
    rejection_reason = db.Column(db.Text, nullable=True)  # Reason for rejection
    
    # Relationships
    item = relationship("Item", back_populates="proofs")
    user = relationship("User")

# Helper functions for database operations
def create_user(name, email, password, is_admin=False, profile_picture=None, 
               phone_number=None, email_notifications=True, sms_notifications=False):
    user = User.query.filter_by(email=email).first()
    if user:
        return None
    
    new_user = User(
        name=name,
        email=email,
        phone_number=phone_number,
        is_admin=is_admin,
        profile_picture=profile_picture,
        email_notifications=email_notifications,
        sms_notifications=sms_notifications
    )
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    return new_user

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def get_user_by_id(user_id):
    return User.query.get(user_id)

def create_item(item_type, title, description, category, date, location, 
               contact_info, image_data, user_id, latitude=None, longitude=None):
    new_item = Item(
        item_type=item_type,
        title=title,
        description=description,
        category=category,
        date=date,
        location=location,
        contact_info=contact_info,
        image_data=image_data,
        user_id=user_id,
        latitude=latitude,
        longitude=longitude
    )
    
    db.session.add(new_item)
    db.session.commit()
    return new_item

def get_item_by_id(item_id):
    return Item.query.get(item_id)

def get_all_items():
    return Item.query.all()

def get_items_by_type(item_type):
    return Item.query.filter_by(item_type=item_type).all()

def get_items_by_user(user_id):
    return Item.query.filter_by(user_id=user_id).all()

def get_pending_items():
    return Item.query.filter_by(status='pending').all()

def delete_item(item_id, user_id):
    """Delete an item from the database. Only allows deletion by the item owner."""
    item = Item.query.get(item_id)
    if not item or item.user_id != user_id:
        return False
    
    db.session.delete(item)
    db.session.commit()
    return True

def update_item_status(item_id, status, admin_id=None):
    item = Item.query.get(item_id)
    if not item:
        return False
        
    item.status = status
    if status == 'verified' and admin_id:
        item.verified_by = admin_id
    
    db.session.commit()
    return True

def claim_item(item_id, user_id):
    item = Item.query.get(item_id)
    if not item:
        return False
        
    item.status = 'claimed'
    item.claimed_by = user_id
    
    db.session.commit()
    return True

def search_items(query, category=None, item_type=None, status=None):
    search_query = "%" + query.lower() + "%"
    
    # Start with base query
    items_query = Item.query
    
    # Apply filters
    if category:
        items_query = items_query.filter_by(category=category)
    if item_type:
        items_query = items_query.filter_by(item_type=item_type)
    if status:
        items_query = items_query.filter_by(status=status)
    
    # Apply search terms
    items_query = items_query.filter(
        db.or_(
            db.func.lower(Item.title).like(search_query),
            db.func.lower(Item.description).like(search_query),
            db.func.lower(Item.location).like(search_query)
        )
    )
    
    return items_query.all()

def create_message(sender_id, recipient_id, subject, content, parent_id=None):
    message = Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        subject=subject,
        content=content,
        parent_id=parent_id
    )
    
    db.session.add(message)
    db.session.commit()
    return message

def get_user_messages(user_id):
    return Message.query.filter_by(recipient_id=user_id).order_by(Message.created_at.desc()).all()

def get_message_thread(message_id):
    # Get the root message of the thread
    message = Message.query.get(message_id)
    if not message:
        return []
    
    # If this is a reply, find the root message
    root_message = message
    while root_message.parent_id:
        root_message = Message.query.get(root_message.parent_id)
    
    # Get all messages in the thread
    thread = [root_message]
    thread.extend(Message.query.filter_by(parent_id=root_message.id).order_by(Message.created_at).all())
    
    return thread

def submit_proof(item_id, user_id, description, evidence=None):
    proof = Proof(
        item_id=item_id,
        user_id=user_id,
        description=description,
        evidence=evidence
    )
    
    db.session.add(proof)
    db.session.commit()
    return proof

def get_proofs_for_item(item_id):
    return Proof.query.filter_by(item_id=item_id).all()

def mark_message_as_read(message_id):
    message = Message.query.get(message_id)
    if message:
        message.read = True
        db.session.commit()
        return True
    return False

def count_unread_messages(user_id):
    return Message.query.filter_by(recipient_id=user_id, read=False).count()

# Create default admin user if it doesn't exist
def create_default_admin():
    admin = User.query.filter_by(email='admin@lostandfound.com').first()
    if not admin:
        create_user(
            name="Admin",
            email="admin@lostandfound.com",
            password="admin123",
            is_admin=True,
            phone_number=None,
            email_notifications=True,
            sms_notifications=False
        )

# Note: This function will be called from app.py within an app context

def archive_expired_items():
    """Archive items that have passed their expiry date"""
    from datetime import datetime
    
    # Find items that have expired and aren't claimed or already archived
    expired_items = Item.query.filter(
        Item.expiry_date <= datetime.utcnow().date(),
        Item.status.in_(['pending', 'verified'])
    ).all()
    
    for item in expired_items:
        item.status = 'archived'
        item.archived_at = datetime.utcnow()
        
        # Notify the owner
        owner = get_user_by_id(item.user_id)
        if owner and owner.email_notifications:
            from flask_mail import Message
            from app import mail
            
            msg = Message(
                subject=f"Your Item Has Been Archived - {item.title}",
                recipients=[owner.email]
            )
            msg.body = f"""
Dear {owner.name},

Your {item.item_type} item "{item.title}" has been automatically archived as it has reached its expiry date.
If you wish to extend the listing, please log in to your account and update the item.

Item Details:
- Type: {item.item_type.capitalize()}
- Category: {item.category}
- Location: {item.location}
- Date: {item.date.strftime('%B %d, %Y')}

Best regards,
Lost and Found Portal Team
            """
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send archive notification email: {e}")
    
    # Commit all changes
    if expired_items:
        db.session.commit()
    
    return len(expired_items)
