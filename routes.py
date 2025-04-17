import os
import base64
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, mail
import models
from forms import LoginForm, RegistrationForm, ItemForm, SearchForm
from utils import resize_and_convert_image, send_verification_email, send_match_notification, find_potential_matches

@app.route('/')
def index():
    # Get 5 most recent verified items of each type
    lost_items = [item for item in models.get_items_by_type('lost') 
                 if item.status == 'verified'][-5:]
    found_items = [item for item in models.get_items_by_type('found') 
                  if item.status == 'verified'][-5:]
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
        
        # Create new user
        user = models.create_user(
            name=form.name.data,
            email=form.email.data,
            password=form.password.data
        )
        
        if user:
            flash('Account created! You can now log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error creating account.', 'danger')
    
    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_items = models.get_items_by_user(current_user.id)
    return render_template('dashboard.html', items=user_items)

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
    
    return render_template('item_details.html', item=item, owner=owner, 
                          is_owner=is_owner, is_admin=is_admin, 
                          potential_matches=potential_matches)

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
    
    # Send email notification to owner
    owner = models.get_user_by_id(item.user_id)
    if owner:
        send_verification_email(owner.email, item)
    
    # Find potential matches and notify users
    potential_matches = find_potential_matches(item)
    for matched_item in potential_matches:
        matched_user = models.get_user_by_id(matched_item.user_id)
        if matched_user:
            send_match_notification(matched_user.email, item)
    
    return jsonify({'success': True, 'message': 'Item verified successfully'})

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
        msg = Message(
            subject="Your Item Has Been Claimed - Lost and Found Portal",
            recipients=[owner.email]
        )
        
        msg.body = f"""
        Dear {owner.name},
        
        Your {item.item_type} item "{item.title}" has been claimed by another user.
        
        Please check your dashboard for more details and to get in touch with the claimer.
        
        Thank you for using our Lost and Found Portal!
        
        Best regards,
        The Lost and Found Team
        """
        
        try:
            mail.send(msg)
        except Exception as e:
            print(f"Error sending email: {e}")
    
    return jsonify({'success': True, 'message': 'Item claimed successfully'})

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)
