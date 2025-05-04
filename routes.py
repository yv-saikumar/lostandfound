import os
import base64
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message as FlaskMailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, mail, db
from forms import (
    LoginForm, RegistrationForm, ItemForm, SearchForm, ProfileUpdateForm,
    MessageForm, ReplyMessageForm, ProofOfOwnershipForm, AdminUserForm,
    CategoryForm
)
from models import Message
import models
from utils import (
    process_images, send_verification_email, send_message_email,
    send_match_notification, find_potential_matches,
    calculate_expiry_date, generate_tags
)

@app.context_processor
def inject_unread_messages():
    if current_user.is_authenticated:
        return {'unread_messages_count': models.count_unread_messages(current_user.id)}
    return {'unread_messages_count': 0}

@app.route('/')
def index():
    # Get 5 most recent verified items of each type
    lost_items = models.Item.query.filter_by(
        item_type='lost', status='verified'
    ).order_by(models.Item.created_at.desc()).limit(5).all()
    
    found_items = models.Item.query.filter_by(
        item_type='found', status='verified'
    ).order_by(models.Item.created_at.desc()).limit(5).all()
    
    # Process images for proper display
    def process_item_images(item):
        if item.images:
            processed_images = []
            for image in item.images:
                # If image is already a dict with 'data' key, use it directly
                if isinstance(image, dict) and 'data' in image:
                    img_data = image['data']
                    # If data doesn't already have the prefix, add it
                    if not img_data.startswith('data:image/'):
                        img_data = f'data:image/jpeg;base64,{img_data}'
                    processed_images.append({'data': img_data})
            item.images = processed_images
    
    # Process images for both lost and found items
    for item in lost_items + found_items:
        process_item_images(item)
    
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
            profile_picture_data = process_images([form.profile_picture.data])[0]['data']
        
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

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = models.get_user_by_email(form.email.data)
        if user and user.check_password(form.password.data):
            if user.is_admin:
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Admin login successful.', 'success')
                return redirect(next_page or url_for('admin_dashboard'))
            else:
                flash('Access denied. Admin privileges required.', 'danger')
        else:
            flash('Login failed. Check your email and password.', 'danger')
    
    return render_template('admin_login.html', form=form)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    pending_items = models.get_pending_items()
    return render_template('admin_dashboard.html', pending_items=pending_items)

@app.route('/admin/statistics')
@login_required
def get_statistics():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get counts from database
        total_lost = models.Item.query.filter_by(item_type='lost').count()
        total_found = models.Item.query.filter_by(item_type='found').count()
        total_verified = models.Item.query.filter_by(status='verified').count()
        total_claimed = models.Item.query.filter_by(status='claimed').count()
        
        return jsonify({
            'total_lost': total_lost,
            'total_found': total_found,
            'total_verified': total_verified,
            'total_claimed': total_claimed
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/verify/<int:item_id>', methods=['POST'])
@login_required
def verify_item(item_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'})
    
    try:
        item = models.Item.query.get_or_404(item_id)
        if item.status != 'pending':
            return jsonify({'success': False, 'message': 'This item is not in pending status'})
        
        # Update item status
        item.status = 'verified'
        item.verified_by = current_user.id
        item.verified_at = datetime.utcnow()
        db.session.commit()

        # Notify the item owner
        owner = models.get_user_by_id(item.user_id)
        if owner:
            # Send email notification if enabled
            if owner.email_notifications:
                try:
                    send_verification_email(owner.email, item)
                except Exception as e:
                    print(f"Error sending verification email: {e}")
            
            # Send SMS notification if enabled
            if owner.sms_notifications and owner.phone_number:
                try:
                    send_verification_sms(owner.phone_number, item)
                except Exception as e:
                    print(f"Error sending verification SMS: {e}")

        return jsonify({
            'success': True,
            'message': f'Item "{item.title}" has been verified successfully'
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error verifying item: {e}")
        return jsonify({'success': False, 'message': 'An error occurred while verifying the item'})

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    import datetime
    
    users = models.User.query.all()
    return render_template(
        'admin_users.html', 
        users=users, 
        now=datetime.datetime.utcnow(),
        timedelta=datetime.timedelta
    )

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

@app.route('/admin/categories', methods=['GET', 'POST'])
@login_required
def admin_categories():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    form = CategoryForm()
    if form.validate_on_submit():
        # Check if category already exists
        existing = models.Category.query.filter_by(name=form.name.data).first()
        if existing:
            flash('A category with this name already exists.', 'danger')
        else:
            category = models.Category(
                name=form.name.data,
                is_active=form.is_active.data
            )
            db.session.add(category)
            db.session.commit()
            flash('Category added successfully.', 'success')
        return redirect(url_for('admin_categories'))
    
    categories = models.Category.query.order_by(models.Category.name).all()
    
    # Get items count and items for each category
    items_count = {}
    category_items = {}
    for category in categories:
        # Count all items in this category
        items = models.Item.query.filter_by(category=category.name).all()
        items_count[category.name] = len(items)
        category_items[category.name] = items
    
    return render_template('admin_categories.html', 
                         form=form, 
                         categories=categories, 
                         items_count=items_count,
                         category_items=category_items)

@app.route('/admin/categories/<int:category_id>/toggle', methods=['POST'])
@login_required
def toggle_category(category_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))
    
    category = models.Category.query.get_or_404(category_id)
    category.is_active = not category.is_active
    db.session.commit()
    
    flash(f'Category "{category.name}" has been {"activated" if category.is_active else "deactivated"}.', 'success')
    return redirect(url_for('admin_categories'))

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
        flash('Item not found.', 'danger')
        return redirect(url_for('index'))
        
    form = ProofOfOwnershipForm()
    if form.validate_on_submit():
        # Process evidence image if provided
        evidence_data = None
        if form.evidence.data:
            evidence_data = process_images([form.evidence.data])[0]['data']
        
        # Create proof record
        proof = models.submit_proof(
            item_id=item_id,
            user_id=current_user.id,
            description=form.description.data,
            evidence=evidence_data
        )
        
        if proof:
            # Send notification to item owner
            evidence_html = ""
            if evidence_data:
                evidence_html = f"""
Supporting Evidence Image:
<img src="{evidence_data}" alt="Evidence" style="max-width: 100%; height: auto;">

"""

            message_content = f"""Proof of Ownership Details:
-----------------------------------
Item: {item.title}
Category: {item.category}
Location: {item.location}
Date Found: {item.date.strftime('%B %d, %Y')}

Claimant's Description:
{form.description.data}

{evidence_html}
Please review this claim request and take appropriate action:
1. Verify the provided information against the item details
2. Check any supporting evidence/images provided
3. Contact the claimant for additional verification if needed
4. Approve or reject the claim through the item details page

Important: This is a formal claim request. Please handle it with care and respond promptly.
"""
            # Create message for the item owner
            message = Message(
                sender_id=current_user.id,
                recipient_id=item.user_id,
                subject=f"Proof of Ownership: {item.title}",
                content=message_content
            )
            db.session.add(message)
            
            try:
                db.session.commit()
                # Send email notification if enabled
                if item.owner.email_notifications:
                    send_message_email(item.owner.email, current_user.name, 
                                    f"New Claim Request: {item.title}")
                
                # Send SMS notification if enabled
                if item.owner.sms_notifications and item.owner.phone_number:
                    send_proof_sms(item.owner.phone_number, item, current_user.name)
                    
                flash('Your proof of ownership has been submitted.', 'success')
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error sending notifications: {str(e)}")
                flash('Proof submitted but there was an error sending notifications.', 'warning')
            
            return redirect(url_for('item_details', item_id=item_id))
        else:
            flash('Error submitting proof of ownership.', 'danger')
            
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
            current_user.profile_picture = process_images([form.profile_picture.data])[0]['data']
        
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

@app.route('/new-message', methods=['GET', 'POST'])
@login_required
def new_message():
    form = MessageForm()
    if form.validate_on_submit():
        recipient = models.get_user_by_email(form.recipient_email.data)
        if not recipient:
            flash('Recipient not found.', 'danger')
            return render_template('new_message.html', form=form)
        
        # Process image if provided
        image_data = None
        if form.image.data:
            try:
                image_data = process_images([form.image.data])[0]['data']
            except Exception as e:
                app.logger.error(f"Error processing image: {str(e)}")
                flash('Error processing image attachment.', 'danger')
                return render_template('new_message.html', form=form)
        
        message = Message(
            sender_id=current_user.id,
            recipient_id=recipient.id,
            subject=form.subject.data,
            content=form.content.data,
            image=image_data
        )
        db.session.add(message)
        
        try:
            db.session.commit()
            
            # Send email notification if enabled
            if recipient.email_notifications:
                send_message_email(recipient.email, current_user.name, "You have a new message")
            
            flash('Message sent successfully.', 'success')
            return redirect(url_for('messages'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error sending message: {str(e)}")
            flash('Error sending message.', 'danger')
            
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
        # Get recipient (opposite of current user)
        recipient_id = message.sender_id if message.recipient_id == current_user.id else message.recipient_id
        recipient = models.get_user_by_id(recipient_id)
        
        # Process image if provided
        image_data = None
        if form.image.data:
            try:
                image_data = process_images([form.image.data])[0]['data']
            except Exception as e:
                app.logger.error(f"Error processing image: {str(e)}")
                flash('Error processing image attachment.', 'danger')
                return render_template('view_message.html', message=message, thread=thread, form=form)
        
        # Create reply
        reply = Message(
            sender_id=current_user.id,
            recipient_id=recipient_id,
            subject=f"Re: {message.subject}",
            content=form.content.data,
            image=image_data,
            parent_id=message.id
        )
        db.session.add(reply)
        
        try:
            db.session.commit()
            
            # Send email notification if enabled
            if recipient.email_notifications:
                send_message_email(recipient.email, current_user.name, "You have a new message reply")
            
            flash('Reply sent successfully.', 'success')
            return redirect(url_for('view_message', message_id=message_id))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error sending reply: {str(e)}")
            flash('Error sending reply.', 'danger')
    
    return render_template('view_message.html', message=message, thread=thread, form=form)

@app.route('/report/<item_type>', methods=['GET', 'POST'])
@login_required
def report_item(item_type):
    if item_type not in ['lost', 'found']:
        abort(404)
    
    form = ItemForm()
    
    # Get only active categories from database
    categories = [(c.name, c.name) for c in models.Category.query.filter_by(is_active=True).all()]
    
    # Add 'others' option at the end
    categories.append(('others', 'Others'))
    
    # Sort categories alphabetically, keeping 'Others' at the end
    form.category.choices = sorted(categories, key=lambda x: x[1] if x[0] != 'others' else 'z')
    
    if form.validate_on_submit():
        # Process images
        images = []
        if form.images.data:
            images = process_images(form.images.data)
        
        # Calculate expiry date
        expiry_date = calculate_expiry_date(form.expiry_days.data)
        
        # Handle the category
        category = form.category.data
        other_category = None
        if category == 'others':
            other_category = form.other_category.data
            # Create a new category if it doesn't exist
            existing_category = models.Category.query.filter_by(name=other_category).first()
            if not existing_category:
                new_category = models.Category(name=other_category, is_active=True)
                db.session.add(new_category)
                try:
                    db.session.commit()
                except:
                    db.session.rollback()
        
        # Generate tags from title and description
        tags = generate_tags(form.title.data, form.description.data, category)
        
        # Create item
        item = models.Item(
            item_type=item_type,
            title=form.title.data,
            description=form.description.data,
            category=category,
            other_category=other_category,
            date=form.date.data,
            expiry_date=expiry_date,
            location=form.location.data,
            contact_info=form.contact_info.data,
            images=images,
            user_id=current_user.id,
            latitude=form.latitude.data if form.latitude.data else None,
            longitude=form.longitude.data if form.longitude.data else None,
            tags=tags
        )
        
        db.session.add(item)
        db.session.commit()
        
        flash(f'Your {item_type} item has been reported and is pending verification.', 'success')
        
        # Find potential matches
        potential_matches = find_potential_matches(item)
        if potential_matches:
            flash(f'We found {len(potential_matches)} potential matches for your {item_type} item!', 'info')
            # Send notification emails for potential matches
            for matched_item in potential_matches:
                matched_user = models.get_user_by_id(matched_item.user_id)
                if matched_user and matched_user.email_notifications:
                    send_match_notification(matched_user.email, item)
            
        return redirect(url_for('dashboard'))
    
    return render_template('report_item.html', form=form, item_type=item_type)

@app.route('/search', methods=['GET'])
def search():
    form = SearchForm()
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    item_type = request.args.get('item_type', '')
    status = request.args.get('status', '')
    
    # Only search if a query is provided
    items = []
    if query or category or item_type or status:
        items = models.search_items(query, category, item_type, status)
    
    return render_template('search.html', form=form, items=items, query=query)

@app.route('/item/<int:item_id>')
@login_required
def item_details(item_id):
    item = models.get_item_by_id(item_id)
    if not item:
        abort(404)
    form = ProofOfOwnershipForm()
    return render_template('item_details.html', item=item, form=form)

@app.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    try:
        # Check if the CSRF token is valid
        if request.is_json and not request.headers.get('X-CSRFToken'):
            return jsonify({'success': False, 'message': 'CSRF token missing'}), 400

        item = models.get_item_by_id(item_id)
        if not item:
            return jsonify({'success': False, 'message': 'Item not found'})
        
        # Check if user is the item owner
        if item.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'You can only delete your own items'})
        
        if models.delete_item(item_id, current_user.id):
            flash('Item deleted successfully.', 'success')
            return jsonify({'success': True, 'redirect': url_for('dashboard')})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete item'})
    except Exception as e:
        app.logger.error(f"Error deleting item: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while deleting the item'}), 500

@app.route('/proof/<int:proof_id>')
@login_required
def view_proof(proof_id):
    proof = models.Proof.query.get_or_404(proof_id)
    item = models.get_item_by_id(proof.item_id)
    
    # Check if user has permission to view this proof
    if not (current_user.id == item.user_id or current_user.id == proof.user_id or current_user.is_admin):
        abort(403)
    
    return render_template('view_proof.html', proof=proof, item=item)

@app.route('/proof/<int:proof_id>/approve', methods=['POST'])
@login_required
def approve_proof(proof_id):
    proof = models.Proof.query.get_or_404(proof_id)
    item = models.get_item_by_id(proof.item_id)
    
    # Check if user is the item owner
    if current_user.id != item.user_id:
        return jsonify({'success': False, 'message': 'Only the item owner can approve claims'})
    
    try:
        # Update proof status
        proof.status = 'approved'
        
        # Update item status and set claimed_by
        item.status = 'claimed'
        item.claimed_by = proof.user_id
        item.claimed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Notify the claimer
        claimer = models.get_user_by_id(proof.user_id)
        if claimer:
            # Send internal message
            models.create_message(
                sender_id=current_user.id,
                recipient_id=claimer.id,
                subject=f"Claim Approved: {item.title}",
                content=f"""Your claim for the {item.item_type} item "{item.title}" has been approved.

Please arrange with the item owner to collect/return the item.

Best regards,
{current_user.name}"""
            )
            
            # Send email notification
            if claimer.email_notifications:
                msg = Message(
                    subject=f"Claim Approved - {item.title}",
                    recipients=[claimer.email]
                )
                msg.body = f"""
                Dear {claimer.name},
                
                Your claim for the {item.item_type} item "{item.title}" has been approved by {current_user.name}.
                
                Please log in to arrange the collection/return of the item with the owner.
                
                Best regards,
                Lost and Found Portal Team
                """
                mail.send(msg)
            
            # Send SMS notification
            if claimer.sms_notifications and claimer.phone_number:
                try:
                    from sms import send_claim_approved_sms
                    send_claim_approved_sms(claimer.phone_number, item)
                except Exception as e:
                    print(f"Error sending claim approved SMS: {e}")
        
        flash('Claim approved successfully.', 'success')
        return jsonify({'success': True, 'message': 'Claim approved successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})

@app.route('/proof/<int:proof_id>/reject', methods=['POST'])
@login_required
def reject_proof(proof_id):
    proof = models.Proof.query.get_or_404(proof_id)
    item = models.get_item_by_id(proof.item_id)
    
    # Check if user is the item owner
    if current_user.id != item.user_id:
        return jsonify({'success': False, 'message': 'Only the item owner can reject claims'})
    
    try:
        # Update proof status
        proof.status = 'rejected'
        proof.rejected_at = datetime.utcnow()
        proof.rejection_reason = request.json.get('reason', '')
        
        db.session.commit()
        
        # Notify the claimer
        claimer = models.get_user_by_id(proof.user_id)
        if claimer:
            # Send internal message
            models.create_message(
                sender_id=current_user.id,
                recipient_id=claimer.id,
                subject=f"Claim Rejected: {item.title}",
                content=f"""Your claim for the {item.item_type} item "{item.title}" has been rejected.

Reason: {proof.rejection_reason}

If you believe this is a mistake, please submit a new claim with additional proof.

Best regards,
{current_user.name}"""
            )
            
            # Send email notification
            if claimer.email_notifications:
                msg = Message(
                    subject=f"Claim Rejected - {item.title}",
                    recipients=[claimer.email]
                )
                msg.body = f"""
                Dear {claimer.name},
                
                Your claim for the {item.item_type} item "{item.title}" has been rejected by {current_user.name}.
                
                Reason: {proof.rejection_reason}
                
                If you believe this is a mistake, you can submit a new claim with additional proof.
                
                Best regards,
                Lost and Found Portal Team
                """
                mail.send(msg)
            
            # Send SMS notification
            if claimer.sms_notifications and claimer.phone_number:
                try:
                    from sms import send_claim_rejected_sms
                    send_claim_rejected_sms(claimer.phone_number, item)
                except Exception as e:
                    print(f"Error sending claim rejected SMS: {e}")
        
        return jsonify({'success': True, 'message': 'Claim rejected successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})
