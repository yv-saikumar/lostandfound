from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField, FileSize
from wtforms import StringField, PasswordField, TextAreaField, SelectField, HiddenField
from wtforms import DateField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional
import mimetypes
import imghdr

def validate_file_type(form, field):
    if not field.data:
        return
    for file in field.data:
        # Read first few bytes to check if it's really an image
        header = file.read(512)
        file.seek(0)  # Reset file pointer after reading
        
        # Use imghdr to detect image type from content
        image_type = imghdr.what(None, header)
        if image_type not in ['jpeg', 'png']:
            raise ValidationError('One or more files are not valid images. Please upload only JPG/PNG images.')

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
                              validators=[
                                  FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'),
                                  FileSize(max_size=5 * 1024 * 1024)  # 5MB max
                              ])
    email_notifications = BooleanField('Email Notifications', default=True)
    sms_notifications = BooleanField('SMS Notifications', default=False)
    submit = SubmitField('Register')

class ProfileUpdateForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number (Optional, for SMS notifications)', 
                              validators=[Length(max=20)])
    profile_picture = FileField('Profile Picture', 
                              validators=[
                                  FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'),
                                  FileSize(max_size=5 * 1024 * 1024)  # 5MB max
                              ])
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
    category = SelectField('Category', validators=[DataRequired()])
    other_category = StringField('Specify Other Category')
    date = DateField('Date Lost/Found', validators=[DataRequired()], format='%Y-%m-%d')
    expiry_days = SelectField('Auto-archive after', choices=[
        ('30', '30 days'),
        ('60', '60 days'),
        ('90', '90 days'),
        ('180', '180 days'),
        ('365', 'One year'),
        ('never', 'Never')
    ], default='90')
    location = StringField('Location', validators=[DataRequired(), Length(min=3, max=200)])
    contact_info = StringField('Contact Information', validators=[DataRequired(), Length(min=5, max=100)])
    images = MultipleFileField('Images (Optional)', 
                           validators=[
                               FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!'),
                               FileSize(max_size=5 * 1024 * 1024, message='Each file must be 5MB or less'),
                               validate_file_type
                           ])
    latitude = HiddenField('Latitude')
    longitude = HiddenField('Longitude')
    submit = SubmitField('Submit')

    def validate_images(self, field):
        if field.data:
            if len(field.data) > 5:
                raise ValidationError('You can upload a maximum of 5 images')
            for file in field.data:
                if not file.filename:
                    continue
                # Check file size
                file.seek(0, 2)  # Seek to end of file
                size = file.tell()
                file.seek(0)  # Reset file pointer
                if size > 5 * 1024 * 1024:  # 5MB
                    raise ValidationError(f'File {file.filename} is too large. Maximum size is 5MB')

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
    image = FileField('Attach Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Send Message')

class ReplyMessageForm(FlaskForm):
    content = TextAreaField('Reply', validators=[DataRequired(), Length(min=5, max=2000)])
    image = FileField('Attach Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Send Reply')

class ProofOfOwnershipForm(FlaskForm):
    """Form for submitting proof of ownership for claiming an item"""
    description = TextAreaField(
        'Proof Description', 
        validators=[
            DataRequired(),
            Length(min=10, max=1000, message="Description must be between 10 and 1000 characters.")
        ],
        description="Please provide detailed information to prove your ownership. Include:\n" +
                  "- Specific details about the item (brand, model, color, etc.)\n" +
                  "- When and where you lost it\n" +
                  "- Any unique identifying features or markings\n" +
                  "- Serial numbers or receipts if available"
    )
    evidence = FileField(
        'Supporting Evidence',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
        ],
        description="Upload images of receipts, previous photos of the item, or other evidence of ownership"
    )
    submit = SubmitField('Submit Claim Request')

class AdminUserForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone_number = StringField('Phone Number (Optional, for SMS notifications)', 
                              validators=[Length(max=20)])
    password = PasswordField('Password', validators=[Length(min=6)])
    is_admin = BooleanField('Admin Privileges')
    email_notifications = BooleanField('Email Notifications', default=True)
    sms_notifications = BooleanField('SMS Notifications', default=False)
    submit = SubmitField('Save User')

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=3, max=50)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Category')
