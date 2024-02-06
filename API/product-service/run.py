import yaml
import pathlib
from flask import Flask, jsonify, request, make_response

app = Flask(__name__)
catalog = yaml.safe_load(pathlib.Path('data/catalog.yml').read_text())

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

@app.route('/api/product/all', methods=['GET'])
def products():
	ret_headers = getForwardHeaders(request)
	resp = make_response(jsonify({'results': catalog}))
	for key, value in ret_headers.items():
		resp.headers[key] = value
	return resp

@app.route('/api/product/<slug>', methods=['GET'])
def product(slug):
	ret_headers = getForwardHeaders(request)
	response = make_response(jsonify({'message': 'Cannot find product'}), 404)
	
	for item in catalog:
		if item['id'] == slug:
			response = make_response(jsonify({'result': item}))
			break

	for key, value in ret_headers.items():
		response.headers[key] = value
	return response


if __name__ == '__main__':
	app.run(host='0.0.0.0', port=7612)
