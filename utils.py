import base64
from io import BytesIO
from PIL import Image
from flask_mail import Message
from app import mail

def resize_and_convert_image(file_data, max_size=(800, 800)):
    """Resize the image and convert to base64 string"""
    try:
        # Open image from binary data
        img = Image.open(BytesIO(file_data))
        
        # Resize image while maintaining aspect ratio
        img.thumbnail(max_size)
        
        # Save to buffer
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        buffer.seek(0)
        
        # Convert to base64
        img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def send_verification_email(user_email, item):
    """Send email notification when an item is verified"""
    msg = Message(
        subject="Your Item Has Been Verified - Lost and Found Portal",
        recipients=[user_email]
    )
    
    msg.body = f"""
    Dear User,
    
    Your {item.item_type} item "{item.title}" has been verified by our admin team.
    
    Item Details:
    - Description: {item.description}
    - Category: {item.category}
    - Date: {item.date}
    - Location: {item.location}
    
    You can now view this item on the public listing.
    
    Thank you for using our Lost and Found Portal!
    
    Best regards,
    The Lost and Found Team
    """
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_match_notification(user_email, matched_item):
    """Send email notification when a potential match is found"""
    item_type_opposite = "found" if matched_item.item_type == "lost" else "lost"
    
    msg = Message(
        subject="Potential Item Match Found - Lost and Found Portal",
        recipients=[user_email]
    )
    
    msg.body = f"""
    Dear User,
    
    We have found a potential match for your {item_type_opposite} item!
    
    Matched Item Details:
    - Title: {matched_item.title}
    - Description: {matched_item.description}
    - Category: {matched_item.category}
    - Date: {matched_item.date}
    - Location: {matched_item.location}
    
    Please log in to your account to view more details and make a claim if this is your item.
    
    Best regards,
    The Lost and Found Team
    """
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def find_potential_matches(item):
    """Find potential matches for an item based on category, title, and description"""
    from models import get_all_items
    
    # Get opposite item type
    opposite_type = "found" if item.item_type == "lost" else "lost"
    
    # Get all items of the opposite type
    all_items = get_all_items()
    opposite_items = [i for i in all_items if i.item_type == opposite_type and i.status == 'verified']
    
    # Score each item for potential match
    potential_matches = []
    for other_item in opposite_items:
        score = 0
        
        # Same category
        if other_item.category == item.category:
            score += 3
        
        # Title similarity (simple check for common words)
        title_words = set(item.title.lower().split())
        other_title_words = set(other_item.title.lower().split())
        common_title_words = title_words.intersection(other_title_words)
        score += len(common_title_words)
        
        # Description similarity
        desc_words = set(item.description.lower().split())
        other_desc_words = set(other_item.description.lower().split())
        common_desc_words = desc_words.intersection(other_desc_words)
        score += len(common_desc_words) * 0.5
        
        # Location similarity
        if item.location.lower() in other_item.location.lower() or other_item.location.lower() in item.location.lower():
            score += 2
            
        # Add to potential matches if score is high enough
        if score >= 3:
            potential_matches.append((other_item, score))
    
    # Sort by score (highest first) and return
    potential_matches.sort(key=lambda x: x[1], reverse=True)
    return [match[0] for match in potential_matches[:5]]  # Return top 5 matches
