import os
import hashlib
import binascii
from flask import Flask, request, make_response, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
	LoginManager, 
	UserMixin, 
	login_user, 
	logout_user,
	login_required
)

### Initialize and configure

app = Flask(__name__)
login_manager = LoginManager()
db = SQLAlchemy()

USER_DB_USER = 'root' if (os.environ.get('DB_USER')) is None else os.environ.get('DB_USER')
USER_DB_PASS = os.environ.get('db_root_password_user')
USER_DB_HOST = 'mysql' if (os.environ.get('MYSQL_SERVICE_HOST')) is None else os.environ.get('MYSQL_SERVICE_HOST')
USER_DB_PORT = '3306' if (os.environ.get('MYSQL_SERVICE_PORT')) is None else os.environ.get('MYSQL_SERVICE_PORT')
USER_DB_TABL = 'users' if (os.environ.get('DB_TABLE')) is None else os.environ.get('DB_TABLE')
USER_DB_NAME = 'userapi' if (os.environ.get('DB_NAME')) is None else os.environ.get('DB_NAME')

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://{}:{}@{}:{}/{}'.format(
	USER_DB_USER,
	USER_DB_PASS,
	USER_DB_HOST,
	USER_DB_PORT,
	USER_DB_NAME
)

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
}

login_manager.init_app(app)
db.init_app(app)
# db._engine_options['pool_size'] = 10
# db._engine_options['max_overflow'] = 20

### User model class and helper query functions

class User(db.Model, UserMixin):
	__tablename__ = USER_DB_TABL

	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True, nullable=False)
	email = db.Column(db.String(120), unique=True, nullable=False)
	password = db.Column(db.LargeBinary)
	api_key = db.Column(db.LargeBinary, unique=True, nullable=True)

	def __init__(self, **kwargs):
		for prop, value in kwargs.items():
			if hasattr(value, '__iter__') and not isinstance(value, str):
				value = value[0]
			if prop == 'password':
				value = self.hash_pass(prop)
			setattr(self, prop, value)
	
	def hash_pass(self, pwd: str):
		salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
		pwdhash = hashlib.pbkdf2_hmac('sha512', pwd.encode(), salt, 100000)
		pwdhash = binascii.hexlify(pwdhash)
		return (salt + pwdhash)
	
	def verify_pass(self, old_pwd, new_pwd):
		old_pwd = old_pwd.decode('ascii')
		salt = old_pwd[:64]
		old_pwd = old_pwd[64:]
		pwdhash = hashlib.pbkdf2_hmac('sha512', new_pwd.encode(), salt.encode('ascii'), 100000)
		pwdhash = binascii.hexlify(pwdhash).decode('ascii')
		return pwdhash == old_pwd
	
	def encode_api_key(self):
		salt = hashlib.sha256(os.urandom(60)).hexdigest()
		self.api_key = self.hash_pass(salt)
	
	def to_json(self):
		return {
			'id': self.id,
			'username': self.username,
			'email': self.email,
			'pass': self.password
		}

@login_manager.user_loader
def load_user(user_id):
	return User.query.filter_by(id=user_id).filter_by()

@login_manager.request_loader
def request_loader(request):
	api_key = request.headers.get('Authorization')
	if api_key:
		api_key = api_key.replace('Basic ', '', 1)
		user = User.query.filter_by(api_key=api_key).first()
		return user if user else None

### Request handling and routing

def getForwardHeaders(request):
	headers = {}

	span_headers = [
		'x-request-id',
		'x-ot-span-context',
		'x-datadog-trace-id',
		'x-datadog-parent-id',
		'x-datadog-sampling-priority',
		'traceparent',
		'tracestate',
		'x-cloud-trace-context',
		'grpc-trace-bin',
		'sw8',
		'user-agent',
		'cookie',
		'authorization',
		'jwt',
	]

	for shdr in span_headers:
		rhdr = request.headers.get(shdr)
		if rhdr is not None:
			headers[shdr] = rhdr
	
	return headers

@app.route('/api/user/all', methods=['GET'])
def get_users():
	ret_headers = getForwardHeaders(request=request)
	data = []
	for row in User.query.all():
		data.append(row.to_json)
	
	resp = make_response(jsonify({'result': data}))
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@app.route('/api/user/login', methods=['POST'])
def login():
	ret_headers = getForwardHeaders(request=request)
	username = request.form['username']
	password = request.form['password']

	user = User.query.filter_by(username=username).first()

	if user and user.verify_pass(user.password, password):
		user.encode_api_key()
		db.session().commit()
		login_user(user)

		resp = make_response(jsonify({'message': 'logged in', 'api_key': user.api_key}))
		for key, value in ret_headers.items():
			resp.headers[key] = value
		return resp
	
	resp = make_response(jsonify({'message': 'Not logged in'}), 401)
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@app.route('/api/user/create', methods=['POST'])
def register():
	ret_headers = getForwardHeaders(request=request)
	username = request.form['username']
	email = request.form['email']

	user = User.query.filter_by(username=username).first()
	if user:
		for key, value in ret_headers.items():
			resp.headers[key] = value
		return resp
	
	user = User.query.filter_by(email=email).first()
	if user:
		resp = make_response(jsonify({'message': 'email',}), 409)
		for key, value in ret_headers.items():
			resp.headers[key] = value
		return resp
	
	user = User(**request.form)
	db.session.add(user)
	db.session.commit()
	logout_user()

	resp = make_response(jsonify({'message': 'registration successful'}))
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@login_required
@app.route('/api/user/logout', methods=['POST'])
def logout():
	logout_user()
	ret_headers = getForwardHeaders(request=request)
	resp = make_response(jsonify({'message': 'logout successful'}))
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@app.route('/api/user/ping')
def ping():
	return 'healthy'

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8600)