from secret_manager import access_secret
import json
import threading
from flask import Flask, request, jsonify
from scripts.timelogs_crosschecker import cross_check_sync_launcher
from scripts.clickup_timelogs_sync import timelog_sync_launcher
from scripts.zp_timesheet_creator import launch_timesheets_submit
from scripts.resource_calculator import launch_calculator
from scripts.resource_creator import launch_creator
from scripts.available_resources import available_resources_collector

app = Flask(__name__)

def require_api_key(view_function):
    from functools import wraps
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        headers_api_key = request.headers.get("X-API-KEY")
        if headers_api_key != access_secret("kitrum-cloud", "vm_api_key"):
            return jsonify({"error": "Unauthorized"}), 401
        return view_function(*args, **kwargs)
    return decorated_function


@app.route('/sync_cross_check', methods=['POST'])
@require_api_key
def sync_cross_check():
    print(f"Received Request to Sync Cross Check")
    payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=cross_check_sync_launcher, args=(payload_data['start'], payload_data['end'], ))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/push_timelogs_to_zp', methods=['POST'])
@require_api_key
def push_timelogs_to_zp():
    print(f"Received Request to Push Timelogs to Zoho People")
    payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=timelog_sync_launcher, args=(payload_data['start'], payload_data['end'], payload_data['emails']))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/create_timesheets', methods=['POST'])
@require_api_key
def create_timesheets():
    print(f"Received Request to Create Timesheets in Zoho People")
    payload_data = json.loads(request.stream.read().decode())
    print(payload_data)
    thread = threading.Thread(target=launch_timesheets_submit, args=(payload_data['start'], payload_data['end'], payload_data['emails']))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/calculate_resources', methods=['POST'])
@require_api_key
def calculate_resources():
    print(f"Received Request to Calculate Resources")
    # payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=launch_calculator)
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/create_resources', methods=['POST'])
@require_api_key
def create_resources():
    print(f"Received Request to Create Resources")
    payload_data = json.loads(request.stream.read().decode())
    dev_info_id = payload_data['dev_info_id']
    thread = threading.Thread(target=launch_creator, args=(dev_info_id, ))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/update_available_resources', methods=['POST'])
@require_api_key
def update_available_resources():
    print(f"Received Request Update Available Resources")
    # payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=available_resources_collector)
    thread.start()
    return jsonify({'status': 'triggered'}), 200


app.run(host='0.0.0.0', port=5201)
# app.run(host='0.0.0.0', port=7261)
