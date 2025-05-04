import os
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# Configure logging
logger = logging.getLogger(__name__)

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

# Initialize Twilio client
try:
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    logger.info("Twilio client initialized successfully")
except Exception as e:
    logger.error(f"Error initializing Twilio client: {e}")
    client = None

def send_sms(to_number, message):
    """
    Send SMS using Twilio API
    
    Args:
        to_number (str): The recipient's phone number in E.164 format (+1234567890)
        message (str): The message content to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not client:
        logger.error("Twilio client not initialized. Cannot send SMS.")
        return False
        
    # Validate phone number (basic E.164 format check)
    if not to_number.startswith('+'):
        to_number = f"+{to_number}"
        
    try:
        # Send message
        sms = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_number
        )
        logger.info(f"SMS sent successfully to {to_number}. SID: {sms.sid}")
        return True
    except TwilioRestException as e:
        logger.error(f"Twilio error sending SMS to {to_number}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending SMS to {to_number}: {e}")
        return False

def send_verification_sms(phone_number, item):
    """Send SMS notification when an item is verified"""
    message = f"""
Lost & Found Portal: Your {item.item_type} item "{item.title}" has been verified by our admin team.
It is now publicly visible. Login to view details.
"""
    return send_sms(phone_number, message)

def send_match_sms(phone_number, item):
    """Send SMS notification when a potential match is found"""
    message = f"""
Lost & Found Portal: We found a potential match for your {item.item_type} item!
Item: {item.title}
Category: {item.category}
Login to view details and contact information.
"""
    return send_sms(phone_number, message)

def send_claim_sms(phone_number, item, claimer_name):
    """Send SMS notification when an item has been claimed"""
    message = f"""
Lost & Found Portal: Your {item.item_type} item "{item.title}" has been claimed by {claimer_name}.
Login to view details and respond to the claim.
"""
    return send_sms(phone_number, message)

def send_proof_sms(phone_number, item, submitter_name):
    """Send SMS notification when a proof of ownership is submitted"""
    message = f"""
Lost & Found Portal: {submitter_name} has submitted proof of ownership for your {item.item_type} item "{item.title}".
Login to review the proof and respond.
"""
    return send_sms(phone_number, message)

def send_message_sms(phone_number, sender_name, subject, is_reply=False):
    """Send SMS notification when a new message or reply is received"""
    message_type = "reply to" if is_reply else "message"
    message = f"""
Lost & Found Portal: You have received a new {message_type} from {sender_name}
Subject: {subject}
Login to view and respond.
"""
    return send_sms(phone_number, message)

def send_claim_approved_sms(phone_number, item):
    """Send SMS notification when a claim is approved"""
    message = f"""
Lost & Found Portal: Your claim for the {item.item_type} item "{item.title}" has been approved.
Login to arrange collection/return of the item.
"""
    return send_sms(phone_number, message)

def send_claim_rejected_sms(phone_number, item):
    """Send SMS notification when a claim is rejected"""
    message = f"""
Lost & Found Portal: Your claim for the {item.item_type} item "{item.title}" has been rejected.
Login to view the rejection reason and submit a new claim if needed.
"""
    return send_sms(phone_number, message)