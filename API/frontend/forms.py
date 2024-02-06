from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, HiddenField, IntegerField
from wtforms.validators import DataRequired, Email
import email_validator


class LoginForm(FlaskForm):
	username	= StringField('Username',
						id='username_login',
						validators=[DataRequired()]
						)
	password	= PasswordField('Password',
						  id='pwd_login',
						  validators=[DataRequired()]
						  )
	submit		= SubmitField('Login')

class RegistrationForm(FlaskForm):
	username	= StringField('Username',
						id='username_create',
						validators=[DataRequired()]
						)
	email		= StringField('Email',
						id='email_create',
						validators=[DataRequired(), Email()]
						)
	password	= PasswordField('Password',
						id='pwd_create',
						validators=[DataRequired()]
						)
	first_name	= StringField('First Name',
						id='firstname_create',
						validators=[DataRequired()]
						)
	last_name	= StringField('Last Name',
						id='lastname_create',
						validators=[DataRequired()]
						)
	submit		= SubmitField('Register')

class OrderItemForm(FlaskForm):
	product_id	= HiddenField(validators=[DataRequired()])
	quantity	= IntegerField(validators=[DataRequired()])
	order_id	= HiddenField()
	submit		= SubmitField('Update')

class ItemForm(FlaskForm):
	product_id	= HiddenField(validators=[DataRequired()])
	quantity	= IntegerField(validators=[DataRequired()])