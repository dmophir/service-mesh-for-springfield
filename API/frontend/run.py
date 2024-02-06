import os
import forms
import requests
from flask import (
	Flask,
	render_template, 
	session, 
	redirect, 
	url_for, 
	flash, 
	request, 
	current_app as app
)
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, current_user, login_required, logout_user

app = Flask(__name__, static_folder='static')

config = {
	'UPLOAD_FOLDER': 'application/static/images',
	'SECRET_KEY': 'y2BH8xD9pyZhDT5qkyZZRgjcJCMHdQ',
	'WTF_CSRF_SECRET_KEY': 'VyOyqv5Fm3Hs3qB1AmNeeuvPpdRqTJbTs5wKvWCS',
	'ENV': "development",
	'DEBUG': True
}

userapi_url 	= 'http://user-service:8600/api/user/'
orderapi_url 	= 'http://order-service:5181/api/order/'
productapi_url 	= 'http://product-service:7612/api/product/'

for key, value in config.items():
	app.config[key] = value

login_manager = LoginManager(app)
login_manager.login_message = "You must be logged in to access this page."
login_manager.login_view = "frontend.login"

bootstrap = Bootstrap(app)



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

@login_manager.user_loader
def load_user(user_id):
	return None

@app.route('/', methods=['GET'])
def home():
	ret_headers = getForwardHeaders(request)

	if current_user.is_authenticated:
		session['order'] = OrderClient.get_order_from_session()

	try:
		products, ret_headers = ProductClient.get_products(ret_headers)
	except requests.exceptions.ConnectionError:
		products = {
			'results': []
			}
	return render_template('home/index.html', products=products, headers=ret_headers)

@app.route('/register', methods=['GET', 'POST'])
def register():
	ret_headers = getForwardHeaders(request)
	form = forms.RegistrationForm(request.form)

	if request.method == 'POST':
		if form.validate_on_submit():
				user, ret_headers = UserClient.post_user_create(request)
				if user:
					flash('Thanks for register, pelase log in', 'success')
					redr = redirect(url_for('login'))
					for key, value in ret_headers.items():
						redr.headers[key] = value
					return redr
			
		else:
			flash('Errors found, please try again', 'error')
	
	return render_template('register/index.html', form=form, headers=ret_headers)

@app.route('/login', methods=['GET', 'POST'])
def login():
	ret_headers = getForwardHeaders(request)
	if current_user.is_authenticated:
		resp = redirect(url_for('home'))
		resp.headers = ret_headers
		return resp
	
	form = forms.LoginForm(request.form)
	if request.method == 'POST':
		if form.validate_on_submit():
			api_key, ret_headers = UserClient.post_login(request)

			if api_key:
				session['user_api_key'] = api_key
				user, ret_headers = UserClient.get_user(ret_headers)
				session['user'] = user['result']

				order = OrderClient.get_order(ret_headers)
				if order.get('result', False):
					session['order'] = order['result']
						
				flash(f"Welcome back, {session['user']['result']['username']}", 'success')
				redr = redirect(url_for('home'))
				for key, value in ret_headers.items():
					redr.headers[key] = value
				return redr
			
			else:
				flash('Unable to login', 'error')
		else:
			flash('Errors found', 'error')

	return render_template('login/index.html', form=form, headers=ret_headers)

@app.route('/logout', methods=['GET'])
def logout():
	ret_headers = getForwardHeaders(request)
	logout_user()
	resp = redirect(url_for('home'))
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@app.route('/checkout', methods=['GET'])
def summary():
	ret_headers = getForwardHeaders(request)
	if 'user' not in session:
		flash('Please login', 'error')
		redr = redirect(url_for('login'))
		for key, value in ret_headers.items():
			redr.headers[key] = value
		return redr

	if 'order' not in session:
		flash('No order found', 'error')
		redr = redirect(url_for('home'))
		for key, value in ret_headers.items():
			redr.headers[key] = value
		return redr
	
	order, ret_headers = OrderClient.get_order(ret_headers)

	if len(order['result']['items']) == 0:
		flash('No order found', 'error')
		redr = redirect(url_for('home'))
		for key, value in ret_headers.items():
			redr.headers[key] = value
		return redr

	OrderClient.post_checkout(ret_headers)

	redr = redirect(url_for('thank_you'))
	for key, value in ret_headers.items():
		redr.headers[key] = value
	return redr

@app.route('/order/thank-you', methods=['GET'])
def thank_you():
	ret_headers = getForwardHeaders(request)
	if 'user' not in session:
		flash('Please login', 'error')
		redr = redirect(url_for('login'))
		for key, value in ret_headers.items():
			redr.headers[key] = value

	if 'order' not in session:
		flash('No order found', 'error')
		redr = redirect(url_for('home'))
		for key, value in ret_headers.items():
			redr.headers[key] = value

	session.pop('order', None)
	flash('Thank you for your order', 'success')

	return render_template('order/thankyou.html', headers=ret_headers)

@app.route('/ping')
def ping():
	return 'healthy'


class OrderClient:
	@staticmethod
	def get_order(ret_headers):
		headers = {
			'Authorization': 'Basic ' + session['user_api_key']
		}
		for key, value in ret_headers.items():
			headers[key] = value

		url = orderapi_url
		response = requests.request(method="GET", url=url, headers=headers)
		order = response.json()
		ret_headers = getForwardHeaders(response)
		return order, ret_headers
	  
	@staticmethod  
	def post_add_to_cart(product_id, qty=1):
		payload = {
			'product_id': product_id,
			'qty': qty
		}
		url = f'{orderapi_url}add-item'

		headers = {
			'Authorization': 'Basic ' + session['user_api_key']
		}
		response = requests.request("POST", url=url, data=payload, headers=headers)
		if response:
			order = response.json()
			return order

	@staticmethod
	def post_checkout(ret_headers):
		url = f'{orderapi_url}checkout'

		headers = {
			'Authorization': 'Basic ' + session['user_api_key']
		}
		for key, value in ret_headers.items():
			headers[key] = value

		response = requests.request("POST", url=url, headers=headers)
		order = response.json()
		ret_headers = getForwardHeaders(response)
		return order, ret_headers

	@staticmethod
	def get_order_from_session():
		default_order = {
			'items': {},
			'total': 0,
		}
		return session.get('order', default_order)


class ProductClient:
	@staticmethod
	def get_products(ret_headers):
		r = requests.get(f'{productapi_url}all', headers=ret_headers)
		ret_headers = getForwardHeaders(r)
		products = r.json()
		return products, ret_headers

	@staticmethod
	def get_product(slug, ret_headers):
		response = requests.request(method="GET", url=f'{productapi_url}{slug}', headers=ret_headers)
		product = response.json()
		ret_headers = getForwardHeaders(response)
		return product, ret_headers

class UserClient:
	@staticmethod
	def post_login(request):
		ret_headers = getForwardHeaders(request)
		form = forms.LoginForm(request.form)

		api_key = False
		payload = {
			'username': form.username.data,
			'password': form.password.data
		}
		url = f'{userapi_url}login'
		response = requests.request("POST", url=url, data=payload, headers=ret_headers)
		ret_headers = getForwardHeaders(response)
		if response:
			d = response.json()
			if d['api_key'] is not None:
				api_key = d['api_key']
		return api_key, ret_headers

	@staticmethod
	def get_user(ret_headers):
		headers = {
			'Authorization': 'Basic ' + session['user_api_key']
		}
		for key, value in ret_headers.items():
			headers[key] = value

		url = userapi_url
		response = requests.request(method="GET", url=url, headers=headers)
		ret_headers = getForwardHeaders(response)
		user = response.json()
		return user, ret_headers

	@staticmethod
	def post_user_create(request):
		ret_headers = getForwardHeaders(request)
		form = forms.RegistrationForm(request.form)

		user = False
		payload = {
			'email': form.email.data,
			'password': form.password.data,
			'first_name': form.first_name.data,
			'last_name': form.last_name.data,
			'username': form.username.data
		}
		url = f'{userapi_url}create'
		response = requests.request("POST", url=url, data=payload, headers=ret_headers)

		if response:
			user = response.json()
		return user, getForwardHeaders(response)

	@staticmethod
	def does_exist(username):
		url = 'http://cuser-service:5001/api/user/' + username + '/exists'
		response = requests.request("GET", url=url)
		return response.status_code == 200




if __name__ == '__main__':
	app.logger.info('starting frontend')
	app.run(host='0.0.0.0', port=8080)