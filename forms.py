from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, HiddenField
from wtforms import DateField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number (Optional, for SMS notifications)', 
                              validators=[Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    profile_picture = FileField('Profile Picture (Optional)', 
                              validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    email_notifications = BooleanField('Email Notifications', default=True)
    sms_notifications = BooleanField('SMS Notifications', default=False)
    submit = SubmitField('Register')

class ProfileUpdateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number (Optional, for SMS notifications)', 
                              validators=[Length(max=20)])
    profile_picture = FileField('Profile Picture', 
                              validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    email_notifications = BooleanField('Email Notifications')
    sms_notifications = BooleanField('SMS Notifications')
    current_password = PasswordField('Current Password (required to confirm changes)')
    new_password = PasswordField('New Password (leave blank to keep current)', 
                                validators=[Length(min=6, message="Password must be at least 6 characters")])
    confirm_new_password = PasswordField('Confirm New Password', 
                                        validators=[EqualTo('new_password')])
    submit = SubmitField('Update Profile')

class ItemForm(FlaskForm):
    title = StringField('Item Title', validators=[DataRequired(), Length(min=3, max=100)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=10, max=500)])
    category = SelectField('Category', choices=[
        ('electronics', 'Electronics'),
        ('documents', 'Documents'),
        ('clothing', 'Clothing'),
        ('accessories', 'Accessories'),
        ('keys', 'Keys'),
        ('bags', 'Bags'),
        ('others', 'Others')
    ], validators=[DataRequired()])
    date = DateField('Date Lost/Found', validators=[DataRequired()], format='%Y-%m-%d')
    location = StringField('Location', validators=[DataRequired(), Length(min=3, max=200)])
    contact_info = StringField('Contact Information', validators=[DataRequired(), Length(min=5, max=100)])
    image = FileField('Image (Optional)', validators=[FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')])
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    submit = SubmitField('Submit')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('', 'All Categories'),
        ('electronics', 'Electronics'),
        ('documents', 'Documents'),
        ('clothing', 'Clothing'),
        ('accessories', 'Accessories'),
        ('keys', 'Keys'),
        ('bags', 'Bags'),
        ('others', 'Others')
    ])
    item_type = SelectField('Type', choices=[
        ('', 'All Types'),
        ('lost', 'Lost'),
        ('found', 'Found')
    ])
    status = SelectField('Status', choices=[
        ('', 'All Status'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('claimed', 'Claimed')
    ])
    submit = SubmitField('Search')

class MessageForm(FlaskForm):
    recipient_email = StringField('Recipient Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=3, max=100)])
    content = TextAreaField('Message', validators=[DataRequired(), Length(min=5, max=2000)])
    submit = SubmitField('Send Message')

class ReplyMessageForm(FlaskForm):
    content = TextAreaField('Reply', validators=[DataRequired(), Length(min=5, max=2000)])
    submit = SubmitField('Send Reply')

class ProofOfOwnershipForm(FlaskForm):
    description = TextAreaField('Description of Proof', 
                             validators=[DataRequired(), Length(min=10, max=1000)],
                             description="Describe how you can prove this item belongs to you. Include unique identifiers, purchase details, or distinguishing marks.")
    evidence = FileField('Evidence (Optional)', 
                        validators=[FileAllowed(['jpg', 'png', 'jpeg', 'pdf'], 'Images or PDF only!')],
                        description="Upload a photo or document that proves your ownership (receipt, unique markings, etc.)")
    submit = SubmitField('Submit Proof')

class AdminUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6)])
    is_admin = BooleanField('Admin Privileges')
    submit = SubmitField('Save User')
