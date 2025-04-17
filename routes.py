import os
import base64
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, mail, db
import models
from forms import (
    LoginForm, RegistrationForm, ItemForm, SearchForm, ProfileUpdateForm,
    MessageForm, ReplyMessageForm, ProofOfOwnershipForm, AdminUserForm
)
from utils import (
    resize_and_convert_image, send_verification_email, 
    send_match_notification, find_potential_matches
)

@app.route('/')
def index():
    # Get 5 most recent verified items of each type
    lost_items = models.Item.query.filter_by(
        item_type='lost', status='verified'
    ).order_by(models.Item.created_at.desc()).limit(5).all()
    
    found_items = models.Item.query.filter_by(
        item_type='found', status='verified'
    ).order_by(models.Item.created_at.desc()).limit(5).all()
    
    return render_template('index.html', lost_items=lost_items, found_items=found_items)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = models.get_user_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if email already exists
        if models.get_user_by_email(form.email.data):
            flash('Email already registered.', 'danger')
            return render_template('register.html', form=form)
        
        # Process profile picture if uploaded
        profile_picture_data = None
        if form.profile_picture.data:
            profile_picture_data = resize_and_convert_image(form.profile_picture.data.read())
        
        try:
            # Create new user directly with SQLAlchemy
            from models import User
            
            user = User(
                name=form.name.data,
                email=form.email.data,
                phone_number=form.phone_number.data if form.phone_number.data else None,
                profile_picture=profile_picture_data,
                email_notifications=form.email_notifications.data,
                sms_notifications=form.sms_notifications.data
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {str(e)}")
            flash('Error creating account. Please try again.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/reset-sessions')
def reset_sessions():
    logout_user()
    flash('All sessions have been reset due to database migration. Please log in again.', 'warning')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_items = models.get_items_by_user(current_user.id)
    
    # Count unread messages
    unread_count = models.count_unread_messages(current_user.id)
    
    return render_template('dashboard.html', items=user_items, unread_count=unread_count)

@app.route('/report/<item_type>', methods=['GET', 'POST'])
@login_required
def report_item(item_type):
    if item_type not in ['lost', 'found']:
        abort(404)
    
    form = ItemForm()
    if form.validate_on_submit():
        # Process image if uploaded
        image_data = None
        if form.image.data:
            image_data = resize_and_convert_image(form.image.data.read())
        
        # Create item
        item = models.create_item(
            item_type=item_type,
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            date=form.date.data,
            location=form.location.data,
            contact_info=form.contact_info.data,
            image_data=image_data,
            user_id=current_user.id,
            latitude=form.latitude.data if form.latitude.data else None,
            longitude=form.longitude.data if form.longitude.data else None
        )
        
        # Find potential matches
        potential_matches = find_potential_matches(item)
        
        flash(f'Your {item_type} item has been reported and is pending verification.', 'success')
        
        # If there are potential matches, show them
        if potential_matches:
            flash(f'We found {len(potential_matches)} potential matches for your {item_type} item!', 'info')
            # Send notification emails for potential matches
            for matched_item in potential_matches:
                matched_user = models.get_user_by_id(matched_item.user_id)
                if matched_user:
                    send_match_notification(matched_user.email, item)
            
        return redirect(url_for('dashboard'))
    
    return render_template('report_item.html', form=form, item_type=item_type)

@app.route('/item/<item_id>')
def item_details(item_id):
    item = models.get_item_by_id(item_id)
    if not item:
        abort(404)
    
    # Get owner info
    owner = models.get_user_by_id(item.user_id)
    
    # Check if the current user is the owner or an admin
    is_owner = current_user.is_authenticated and current_user.id == item.user_id
    is_admin = current_user.is_authenticated and current_user.is_admin
    
    # Get potential matches if user is authenticated and is owner
    potential_matches = []
    if current_user.is_authenticated and is_owner:
        potential_matches = find_potential_matches(item)
    
    # Get proofs of ownership if admin
    proofs = []
    if is_admin:
        proofs = models.get_proofs_for_item(item_id)
    
    # Get proof form if user is authenticated and not the owner
    proof_form = None
    if current_user.is_authenticated and not is_owner and item.status == 'verified':
        proof_form = ProofOfOwnershipForm()
    
    return render_template(
        'item_details.html', 
        item=item, 
        owner=owner, 
        is_owner=is_owner, 
        is_admin=is_admin, 
        potential_matches=potential_matches,
        proofs=proofs,
        proof_form=proof_form
    )

@app.route('/search', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    results = []
    
    if request.method == 'POST' and form.validate_on_submit():
        results = models.search_items(
            query=form.query.data,
            category=form.category.data if form.category.data else None,
            item_type=form.item_type.data if form.item_type.data else None,
            status=form.status.data if form.status.data else None
        )
    
    return render_template('search.html', form=form, results=results)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    pending_items = models.get_pending_items()
    return render_template('admin_dashboard.html', pending_items=pending_items)

@app.route('/admin/verify/<item_id>', methods=['POST'])
@login_required
def verify_item(item_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Permission denied'})
    
    item = models.get_item_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'})
    
    # Update item status
    models.update_item_status(item_id, 'verified', current_user.id)
    
    # Send notifications to owner
    owner = models.get_user_by_id(item.user_id)
    if owner:
        # Email notification
        if owner.email_notifications:
            send_verification_email(owner.email, item)
        
        # SMS notification if enabled and phone number provided
        if owner.sms_notifications and owner.phone_number:
            from sms import send_verification_sms
            try:
                send_verification_sms(owner.phone_number, item)
            except Exception as e:
                print(f"Error sending SMS notification: {e}")
    
    # Find potential matches and notify users
    potential_matches = find_potential_matches(item)
    for matched_item in potential_matches:
        matched_user = models.get_user_by_id(matched_item.user_id)
        if matched_user:
            # Email notification for potential match
            if matched_user.email_notifications:
                send_match_notification(matched_user.email, item)
            
            # SMS notification for potential match
            if matched_user.sms_notifications and matched_user.phone_number:
                from sms import send_match_sms
                try:
                    send_match_sms(matched_user.phone_number, item)
                except Exception as e:
                    print(f"Error sending match SMS notification: {e}")
    
    return jsonify({'success': True, 'message': 'Item verified successfully'})

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    users = models.User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    user = models.User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        user.name = form.name.data
        user.email = form.email.data
        user.is_admin = form.is_admin.data
        
        if form.password.data:
            user.set_password(form.password.data)
            
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin_users'))
        
    return render_template('admin_edit_user.html', form=form, user=user)

@app.route('/admin/user/new', methods=['GET', 'POST'])
@login_required
def admin_new_user():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
        
    form = AdminUserForm()
    
    if form.validate_on_submit():
        if not form.password.data:
            flash('Password is required when creating a new user.', 'danger')
        else:
            # Check if email already exists
            if models.get_user_by_email(form.email.data):
                flash('Email already registered.', 'danger')
            else:
                # Create new user
                user = models.create_user(
                    name=form.name.data,
                    email=form.email.data,
                    password=form.password.data,
                    is_admin=form.is_admin.data
                )
                
                if user:
                    flash('User created successfully.', 'success')
                    return redirect(url_for('admin_users'))
                else:
                    flash('Error creating user.', 'danger')
    
    return render_template('admin_new_user.html', form=form)

@app.route('/claim/<item_id>', methods=['POST'])
@login_required
def claim_item(item_id):
    item = models.get_item_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Item not found'})
    
    # Check if item can be claimed
    if item.status != 'verified':
        return jsonify({'success': False, 
                      'message': 'This item cannot be claimed. It may be pending verification or already claimed.'})
    
    # Update item status
    models.claim_item(item_id, current_user.id)
    
    # Notify the item owner
    owner = models.get_user_by_id(item.user_id)
    if owner:
        # Email notification
        if owner.email_notifications:
            msg = Message(
                subject="Your Item Has Been Claimed - Lost and Found Portal",
                recipients=[owner.email]
            )
            
            msg.body = f"""
            Dear {owner.name},
            
            Your {item.item_type} item "{item.title}" has been claimed by {current_user.name}.
            
            Please check your dashboard for more details and to get in touch with the claimer.
            
            Thank you for using our Lost and Found Portal!
            
            Best regards,
            The Lost and Found Team
            """
            
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Error sending claim email: {e}")
        
        # SMS notification
        if owner.sms_notifications and owner.phone_number:
            from sms import send_claim_sms
            try:
                send_claim_sms(owner.phone_number, item, current_user.name)
            except Exception as e:
                print(f"Error sending claim SMS: {e}")
    
    return jsonify({'success': True, 'message': 'Item claimed successfully'})

@app.route('/submit-proof/<item_id>', methods=['POST'])
@login_required
def submit_proof(item_id):
    item = models.get_item_by_id(item_id)
    if not item:
        abort(404)
    
    # Check if item can be claimed
    if item.status != 'verified':
        flash('This item cannot be claimed. It may be pending verification or already claimed.', 'danger')
        return redirect(url_for('item_details', item_id=item_id))
    
    # Check if user is not the item owner
    if current_user.id == item.user_id:
        flash('You cannot claim your own item.', 'danger')
        return redirect(url_for('item_details', item_id=item_id))
    
    form = ProofOfOwnershipForm()
    if form.validate_on_submit():
        # Process evidence if uploaded
        evidence_data = None
        if form.evidence.data:
            evidence_data = resize_and_convert_image(form.evidence.data.read())
        
        # Submit proof
        proof = models.submit_proof(
            item_id=item_id,
            user_id=current_user.id,
            description=form.description.data,
            evidence=evidence_data
        )
        
        # Notify the item owner
        owner = models.get_user_by_id(item.user_id)
        if owner:
            # Create an internal message
            models.create_message(
                sender_id=current_user.id,
                recipient_id=owner.id,
                subject=f"Proof of Ownership: {item.title}",
                content=f"""I have submitted proof of ownership for your {item.item_type} item "{item.title}".
                
Please check the proof and respond to this message. If you agree that this item belongs to me, please approve the claim.

Proof Description:
{form.description.data}

Thank you,
{current_user.name}"""
            )
            
            # Send email notification if enabled
            if owner.email_notifications:
                try:
                    msg = Message(
                        subject=f"Proof of Ownership Submitted - {item.title}",
                        recipients=[owner.email]
                    )
                    
                    msg.body = f"""
                    Dear {owner.name},
                    
                    {current_user.name} has submitted proof of ownership for your {item.item_type} item "{item.title}".
                    
                    Please log in to review the proof and respond to the claim.
                    
                    Thank you for using our Lost and Found Portal!
                    
                    Best regards,
                    The Lost and Found Team
                    """
                    
                    mail.send(msg)
                except Exception as e:
                    print(f"Error sending proof email notification: {e}")
            
            # Send SMS notification if enabled
            if owner.sms_notifications and owner.phone_number:
                from sms import send_proof_sms
                try:
                    send_proof_sms(owner.phone_number, item, current_user.name)
                except Exception as e:
                    print(f"Error sending proof SMS notification: {e}")
        
        flash('Your proof of ownership has been submitted.', 'success')
        return redirect(url_for('item_details', item_id=item_id))
    
    return redirect(url_for('item_details', item_id=item_id))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileUpdateForm()
    
    if request.method == 'GET':
        # Pre-fill form with current user data
        form.name.data = current_user.name
        form.email.data = current_user.email
        form.phone_number.data = current_user.phone_number
        form.email_notifications.data = current_user.email_notifications
        form.sms_notifications.data = current_user.sms_notifications
    
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return render_template('profile.html', user=current_user, form=form)
        
        # Update profile
        current_user.name = form.name.data
        current_user.phone_number = form.phone_number.data
        current_user.email_notifications = form.email_notifications.data
        current_user.sms_notifications = form.sms_notifications.data
        
        # Update email if changed
        if form.email.data != current_user.email:
            # Check if email already exists
            if models.get_user_by_email(form.email.data) and models.get_user_by_email(form.email.data).id != current_user.id:
                flash('Email already registered by another user.', 'danger')
                return render_template('profile.html', user=current_user, form=form)
            current_user.email = form.email.data
        
        # Update password if provided
        if form.new_password.data:
            current_user.set_password(form.new_password.data)
        
        # Update profile picture if uploaded
        if form.profile_picture.data:
            current_user.profile_picture = resize_and_convert_image(form.profile_picture.data.read())
        
        # Check if SMS notifications enabled but no phone
        if current_user.sms_notifications and not current_user.phone_number:
            flash('SMS notifications require a phone number. Please add a phone number or disable SMS notifications.', 'warning')
            current_user.sms_notifications = False
            
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html', user=current_user, form=form)

@app.route('/messages')
@login_required
def messages():
    # Get user's messages
    user_messages = models.get_user_messages(current_user.id)
    
    # Count unread messages
    unread_count = models.count_unread_messages(current_user.id)
    
    return render_template('messages.html', messages=user_messages, unread_count=unread_count)

@app.route('/messages/new', methods=['GET', 'POST'])
@login_required
def new_message():
    form = MessageForm()
    
    if form.validate_on_submit():
        # Get recipient
        recipient = models.get_user_by_email(form.recipient_email.data)
        if not recipient:
            flash('Recipient email not found.', 'danger')
            return render_template('new_message.html', form=form)
        
        # Create message
        message = models.create_message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            subject=form.subject.data,
            content=form.content.data
        )
        
        flash('Message sent successfully.', 'success')
        return redirect(url_for('messages'))
    
    return render_template('new_message.html', form=form)

@app.route('/messages/<int:message_id>', methods=['GET', 'POST'])
@login_required
def view_message(message_id):
    message = models.Message.query.get_or_404(message_id)
    
    # Check if user is allowed to view this message
    if message.recipient_id != current_user.id and message.sender_id != current_user.id:
        abort(403)
    
    # Mark message as read if current user is the recipient
    if message.recipient_id == current_user.id and not message.read:
        models.mark_message_as_read(message_id)
    
    # Get the thread of messages
    thread = models.get_message_thread(message_id)
    
    # Reply form
    form = ReplyMessageForm()
    
    if form.validate_on_submit():
        # Create reply
        reply = models.create_message(
            sender_id=current_user.id,
            recipient_id=message.sender_id if message.recipient_id == current_user.id else message.recipient_id,
            subject=f"Re: {message.subject}",
            content=form.content.data,
            parent_id=message.id if not message.parent_id else message.parent_id
        )
        
        flash('Reply sent successfully.', 'success')
        return redirect(url_for('view_message', message_id=message_id))
    
    return render_template('view_message.html', message=message, thread=thread, form=form)
