import json
import threading
from flask import Flask, request, jsonify
from scripts.timelogs_crosschecker import cross_check_sync_launcher
from scripts.clickup_timelogs_sync import timelog_sync_launcher
from scripts.zp_timesheet_creator import launch_timesheets_submit

app = Flask(__name__)


@app.route('/sync_cross_check', methods=['POST'])
def sync_cross_check():
    print(f"Received Request to Sync Cross Check")
    payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=cross_check_sync_launcher, args=(payload_data['start'], payload_data['end'], ))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/push_timelogs_to_zp', methods=['POST'])
def push_timelogs_to_zp():
    print(f"Received Request to Push Timelogs to Zoho People")
    payload_data = json.loads(request.stream.read().decode())
    thread = threading.Thread(target=timelog_sync_launcher, args=(payload_data['start'], payload_data['end'], payload_data['emails']))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


@app.route('/create_timesheets', methods=['POST'])
def create_timesheets():
    print(f"Received Request to Create Timesheets in Zoho People")
    payload_data = json.loads(request.stream.read().decode())
    print(payload_data)
    thread = threading.Thread(target=launch_timesheets_submit, args=(payload_data['start'], payload_data['end'], payload_data['emails']))
    thread.start()
    return jsonify({'status': 'triggered'}), 200


app.run(host='0.0.0.0', port=5201)
