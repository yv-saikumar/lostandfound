import os
import base64
from io import BytesIO
from PIL import Image, ExifTags, ImageOps
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from geopy.distance import geodesic
from werkzeug.utils import secure_filename
from flask import current_app
import uuid


def process_images(image_files, max_size=(800, 800), quality=85):
    """Process multiple images for storage"""
    processed_images = []
    
    for image_file in image_files:
        if not image_file:
            continue
            
        try:
            # Generate a secure filename with UUID
            original_filename = secure_filename(image_file.filename)
            file_extension = os.path.splitext(original_filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Open and process image
            image = Image.open(image_file)
            
            # Extract EXIF data
            exif_data = {}
            if hasattr(image, '_getexif') and image._getexif():
                for tag_id in image._getexif():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_data[tag] = image._getexif()[tag_id]
            
            # Auto-orient image based on EXIF
            image = ImageOps.exif_transpose(image)
            
            # Resize maintaining aspect ratio
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save to buffer for base64 encoding
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            # Add proper data URI prefix for web display
            mime_type = 'image/jpeg'
            img_data = f'data:{mime_type};base64,{img_str}'
            
            processed_images.append({
                'filename': unique_filename,
                'data': img_data,
                'exif': exif_data
            })
            
        except Exception as e:
            current_app.logger.error(f"Error processing image {image_file.filename}: {str(e)}")
            continue
    
    return processed_images

def generate_tags(title, description, category):
    """Generate searchable tags from item data"""
    try:
        # Combine text
        text = f"{title} {description} {category}"
        
        # Tokenize (using simple split as fallback if NLTK fails)
        try:
            tokens = word_tokenize(text.lower())
        except LookupError:
            # Fallback to simple word splitting if NLTK fails
            tokens = text.lower().split()
        
        # Remove stopwords and lemmatize
        try:
            stop_words = set(stopwords.words('english'))
        except LookupError:
            # Fallback to a basic set of stopwords
            stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
                         'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
                         'that', 'the', 'to', 'was', 'were', 'will', 'with'}
        
        try:
            lemmatizer = WordNetLemmatizer()
            tags = []
            for token in tokens:
                if token not in stop_words and token.isalnum():
                    lemma = lemmatizer.lemmatize(token)
                    if len(lemma) > 2:  # Only include words longer than 2 characters
                        tags.append(lemma)
        except LookupError:
            # Fallback to just filtering without lemmatization
            tags = [token for token in tokens if token not in stop_words 
                   and token.isalnum() and len(token) > 2]
        
        # Remove duplicates and sort
        return sorted(list(set(tags)))
    except Exception as e:
        print(f"Error generating tags: {e}")
        # Return basic tags if everything fails
        return [w.lower() for w in text.split() if len(w) > 2]

def calculate_expiry_date(days_str):
    """Calculate expiry date based on selected duration"""
    if days_str == 'never':
        return None
        
    days = int(days_str)
    return datetime.utcnow().date() + timedelta(days=days)

def find_nearby_items(latitude, longitude, max_distance=10):
    """Find items within max_distance km of coordinates"""
    from models import Item
    
    nearby_items = []
    all_items = Item.query.filter(
        Item.latitude.isnot(None),
        Item.longitude.isnot(None),
        Item.status == 'verified'
    ).all()
    
    for item in all_items:
        distance = geodesic(
            (latitude, longitude),
            (item.latitude, item.longitude)
        ).kilometers
        
        if distance <= max_distance:
            item_dict = item.to_dict()
            item_dict['distance'] = round(distance, 2)
            nearby_items.append(item_dict)
    
    return sorted(nearby_items, key=lambda x: x['distance'])

def find_potential_matches(item):
    """Find potential matches using tags and location"""
    from models import Item
    
    # Get opposite item type
    opposite_type = 'found' if item.item_type == 'lost' else 'lost'
    
    # Get all verified items of opposite type
    potential_matches = Item.query.filter_by(
        item_type=opposite_type,
        status='verified'
    ).all()
    
    # Score each item for matching
    scored_matches = []
    for match in potential_matches:
        score = 0
        
        # Check if tags overlap
        if item.tags and match.tags:
            common_tags = set(item.tags) & set(match.tags)
            score += len(common_tags) * 10
        
        # Check location if coordinates available
        if (item.latitude and item.longitude and 
            match.latitude and match.longitude):
            distance = geodesic(
                (item.latitude, item.longitude),
                (match.latitude, match.longitude)
            ).kilometers
            
            # Add distance-based score (closer = higher score)
            if distance <= 1:  # Within 1km
                score += 50
            elif distance <= 5:  # Within 5km
                score += 30
            elif distance <= 10:  # Within 10km
                score += 20
        
        # Check category
        if item.category == match.category:
            score += 20
        
        # Check date proximity (within 7 days)
        date_diff = abs((item.date - match.date).days)
        if date_diff <= 7:
            score += max(0, 20 - (date_diff * 2))  # Decrease score by 2 for each day difference
        
        if score > 0:
            scored_matches.append((match, score))
    
    # Sort by score and return top matches
    scored_matches.sort(key=lambda x: x[1], reverse=True)
    return [match for match, score in scored_matches[:5]]

def send_verification_email(recipient_email, item):
    """Send email notification when an item is verified"""
    from flask_mail import Message
    from app import mail
    
    msg = Message(
        subject=f"Your Item Has Been Verified - {item.title}",
        recipients=[recipient_email]
    )
    msg.body = f"""
Dear {item.owner.name},

Your {item.item_type} item "{item.title}" has been verified by our admin team and is now visible to other users.

Item Details:
- Type: {item.item_type.capitalize()}
- Category: {item.category}
- Location: {item.location}
- Date: {item.date.strftime('%B %d, %Y')}

You will be notified if someone claims this item or if we find potential matches.

Thank you for using our Lost and Found Portal!

Best regards,
Lost and Found Portal Team
    """
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send verification email: {e}")

def send_match_notification(recipient_email, matched_item):
    """Send email notification for potential item match"""
    from flask_mail import Message
    from app import mail
    
    msg = Message(
        subject=f"Potential Match Found - {matched_item.title}",
        recipients=[recipient_email]
    )
    msg.body = f"""
Dear {matched_item.owner.name},

We found a potential match for your {matched_item.item_type} item "{matched_item.title}"!

Please log in to your account to view the potential match and check if it's your item.

Item Details:
- Type: {matched_item.item_type.capitalize()}
- Category: {matched_item.category}
- Location: {matched_item.location}
- Date: {matched_item.date.strftime('%B %d, %Y')}

Thank you for using our Lost and Found Portal!

Best regards,
Lost and Found Portal Team
    """
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send match notification email: {e}")

def send_message_email(recipient_email, sender_name, subject):
    """Send email notification when a new message is received"""
    from flask_mail import Message
    from app import mail
    
    msg = Message(
        subject=f"New Message from {sender_name} - Lost and Found Portal",
        recipients=[recipient_email]
    )
    msg.body = f"""
Dear User,

You have received a new message from {sender_name}.

Subject: {subject}

Please log in to your account to view the message and reply.

Best regards,
Lost and Found Portal Team
    """
    
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Failed to send message notification email: {e}")
