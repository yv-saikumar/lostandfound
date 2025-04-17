from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FileField, HiddenField
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
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

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
    image = FileField('Image (Optional)')
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
