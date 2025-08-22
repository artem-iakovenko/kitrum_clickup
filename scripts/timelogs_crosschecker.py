import time
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from scripts.help_functions import datetime_str_to_unix, str_to_date, get_working_days, get_timelogs, send_slack_notification
from datetime import datetime, timezone, timedelta
import pytz
import json
from secret_manager import access_secret
from scripts.config import SLACK_CHANNEL_TIMELOGS
from secret_manager import access_secret

with open("project_files/user_timezones.json", "r") as json_file:
    USER_TIMEZONES = json.load(json_file)

SPREADSHEET_ID = "1zWpnDFr0QVeh8mvqx1PGtiWFiL-Z_vG3xiDhWEDP11Q"
SHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

DEFAULT_TIMEZONE = "Europe/Kiev"
LEAVES_LISTS = ['901204775879']


class LogSyncer:
    def __init__(self, start_date, end_date, custom_user_emails):
        self.clickup_headers = {"Content-Type": "application/json", "Authorization": access_secret('kitrum-cloud', "clickup")}
        self.start_date = start_date
        self.end_date = end_date
        self.search_start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
        self.search_end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        self.start_date_unix = None
        self.end_date_unix = None
        self.custom_user_emails = custom_user_emails
        self.team_id = None
        self.clickup_users = []
        self.tracked_time_by_user = {}
        self.tracked_time_by_user_list = []
        self.all_timelogs = []

    def get_all_clickup_users(self):
        response = requests.get("https://api.clickup.com/api/v2/team", headers=self.clickup_headers)
        team_data = response.json()['teams'][0]
        self.team_id = team_data['id']
        self.clickup_users = team_data['members']

    def get_timelogs(self, user_id):
        response = requests.get(f"https://api.clickup.com/api/v2/team/{self.team_id}/time_entries?assignee={user_id}&start_date={self.start_date_unix}&end_date={self.end_date_unix}", headers=self.clickup_headers)
        return response.json()['data'] if response.status_code == 200 else []

    def get_zp_timelogs(self, user_email):
        zp_tracked = 0
        zp_tracked_billable = 0
        for timelog in self.all_timelogs:
            if timelog['employeeMailId'] != user_email:
                continue
            billing_status = timelog['billingStatus']
            zp_hours_in_mins = round(float(timelog['hoursInMins']), 2)
            zp_hours = float(zp_hours_in_mins) / 60
            zp_tracked += zp_hours
            if billing_status == "billable":
                zp_tracked_billable += zp_hours

        return [round(zp_tracked, 2), round(zp_tracked_billable, 2)]

    def launcher(self):
        self.all_timelogs = get_timelogs(self.start_date, self.end_date)
        print(len(self.all_timelogs))
        # ADD +- 2 DAYS TO AVOID TIMEZONE ISSUES
        self.start_date_unix = datetime_str_to_unix(self.search_start_date, 0, 0)
        self.end_date_unix = datetime_str_to_unix(self.search_end_date, 23, 59)
        # GET ALL CLICKUP USERS
        self.get_all_clickup_users()

        expected_hours = get_working_days(self.start_date, self.end_date) * 8
        print(f"EXPECTED: {expected_hours}")
        counter = 0
        for user in self.clickup_users:
            counter += 1
            user_id = user['user']['id']
            user_email = user['user']['email']
            if self.custom_user_emails and user_email not in self.custom_user_emails:
                continue
            print("-----------------------------")
            print(f"{counter}/{len(self.clickup_users)}. Current User Email: {user_email}")
            user_timelogs = self.get_timelogs(user_id)
            if not user_timelogs:
                print(f"\tNo Timelogs Available")
            # user_timezone = get_timezone(user_id) or DEFAULT_TIMEZONE
            user_timezone = USER_TIMEZONES[user_email] if user_email in USER_TIMEZONES else DEFAULT_TIMEZONE

            print(f"\tUser Timezone: {user_timezone}")
            zp_parsed = self.get_zp_timelogs(user_email)
            zp_tracked = zp_parsed[0]
            zp_tracked_billable = zp_parsed[1]

            total_tracked_hours = 0
            total_leave_hours = 0
            for user_timelog in user_timelogs:
                # CONVERT LOG DATE TO USER TIMEZONE
                timelog_start_unix = int(user_timelog['start'])
                dt_utc = datetime.fromtimestamp(timelog_start_unix / 1000, tz=timezone.utc)
                dt_default_timezone = dt_utc.astimezone(pytz.timezone(DEFAULT_TIMEZONE))
                dt_user_timezone = dt_default_timezone.astimezone(pytz.timezone(user_timezone))
                timelog_date = dt_user_timezone.strftime('%Y-%m-%d')
                timelog_location = user_timelog['task_location'] if 'task_location' in user_timelog else None
                timelog_list_id = timelog_location['list_id'] if timelog_location else ""
                timelog_duration = int(user_timelog['duration'])
                timelog_duration_hours = timelog_duration / (1000 * 60 * 60)
                if str_to_date(self.start_date) <= str_to_date(timelog_date) <= str_to_date(self.end_date):
                    pass
                else:
                    continue
                if timelog_list_id in LEAVES_LISTS:
                    total_leave_hours += timelog_duration_hours
                else:
                    total_tracked_hours += timelog_duration_hours
            print(f"\tTotal Tracked: {total_tracked_hours}")
            print(f"\tTotal Leave: {total_leave_hours}")
            print(f"\tTotal: {total_tracked_hours + total_leave_hours}")
            print(total_tracked_hours)
            if round(float(total_tracked_hours), 2) > 0:
                self.tracked_time_by_user[user_email] = {"business_hours": round(float(expected_hours), 2), "tracked_hours": round(float(total_tracked_hours), 2), "leave_hours": round(float(total_leave_hours), 2), "zp_tracked": round(float(zp_tracked), 2)}
                self.tracked_time_by_user_list.append([user_email, round(float(expected_hours), 2), round(float(total_tracked_hours), 2), round(float(total_leave_hours), 2), round(float(zp_tracked), 2), zp_tracked_billable])


def cross_check_sync_launcher(start_date, end_date):
    sheets_json = json.loads(access_secret("kitrum-cloud", "google_sheets_service"))
    creds = service_account.Credentials.from_service_account_info(
        sheets_json, scopes=SHEET_SCOPES
    )
    service = build('sheets', 'v4', credentials=creds)
    date_obj = datetime.strptime(end_date, "%Y-%m-%d")
    month_name = date_obj.strftime("%B")
    working_range = f"{month_name}!A7:F"
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=working_range,
        body={}
    ).execute()
    # GET LOGS
    logs_handler = LogSyncer(start_date, end_date, None)
    logs_handler.launcher()
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=working_range,
        valueInputOption='USER_ENTERED',
        body={"values": logs_handler.tracked_time_by_user_list}
    ).execute()
    # send_slack_notification(SLACK_CHANNEL_TIMELOGS, f"Crosscheck data has been formed for range *{start_date} - {end_date}*")




