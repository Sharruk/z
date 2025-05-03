from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Length(min=10, max=15)])
    address = TextAreaField('Address')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Register as', choices=[
        ('customer', 'Customer'), 
        ('restaurant', 'Restaurant Owner'), 
        ('delivery', 'Delivery Partner')
    ])
    submit = SubmitField('Register')

class CompleteProfileForm(FlaskForm):
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=10, max=15)])
    address = TextAreaField('Delivery Address', validators=[DataRequired()])
    submit = SubmitField('Complete Profile')
