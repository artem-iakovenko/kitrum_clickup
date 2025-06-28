import time
import requests
from credentials.api_creds import CLICKUP_HEADERS
from scripts.help_functions import datetime_str_to_unix, str_to_date, get_zp_projects, get_zp_job_by_clickup_id, get_zp_job_by_name, update_zp_job, get_zp_employees, format_hours, create_zp_job, update_zp_project, get_zp_logs, push_timelogs_to_zp, delete_time_tracked, get_clickup_task_by_id, send_slack_notification
from datetime import datetime, timezone, timedelta
import pytz
import json
from scripts.config import SLACK_CHANNEL_TIMELOGS


with open("project_files/user_timezones.json", "r") as json_file:
    USER_TIMEZONES = json.load(json_file)

DEFAULT_TIMEZONE = "Europe/Kiev"
LEAVES_LISTS = ['901204775879']
COMMERCIAL_SPACES = ['90121864869']
OUTSOURCE_SPACES = ['90123406123']
PRESALE_LISTS = ['901201952497']
INTERNAL_ACTIVITIES_LISTS = ['901205350291']
ADMIN_TASK_TRACKER_LISTS = ['900200672359']
INTERVIEW_TASK_TYPES = [1013]
BENCH_TASK_TYPES = [1014]
PRESALE_TASK_TYPES = [1007]
INTERNAL_PROJECT_LISTS = {
    # JAVA UNIT
    "901202188927": "378942000024070314",
    "901202189134": "378942000024070314",
    # CTO
    "901205193720": "378942000026337117",
    "901205193756": "378942000026337117",
    # QA
    "901209566746": "378942000031293378",
    # PM
    "901207881892": "378942000028727416",
    # BA
    "901206162641": "378942000007241305",
    # MARKETING
    "901200697017": "378942000013754065"
}

CUSTOM_TASKS_MAPPING = {}
DEFAULT_PROJECTS_BY_DEPARTMENT = {
    "QA Unit": "378942000031293378",
    "HR/Office": "378942000000349037",
    "Outbound": "378942000000199401",
    "Client Development": "378942000000339807",
    "Technology": "378942000026337117",
    "Finance & Legal": "378942000030501276",
    "Brand Marketing Team": "378942000013754065",
    "Java Unit": "378942000024070314",
    "Operations Contractors": "378942000009246025",
    "Finance & Legal Contractors": "378942000000530585",
    "HR/Office Contractors": "378942000027350743",
    "Client Development Contractors": "378942000000339807",
    "Outbound Contractors": "378942000000199401",
    "Brand Marketing Contractors": "378942000013754065",
    "Delivery Contractors": "378942000028931765",
    "Talent Acquisition Contractors": "378942000000390015",
    "Finance Team": "378942000000530585",
    "Legal Team": "378942000030507278",
    "Human Resources": "378942000027350743",
    "Operations": "378942000026019329",
    "Resource Management": "378942000028041920",
    "Recruiting": "378942000000390015",
    "CGT": "378942000030501302",
    "Client Development Team": "378942000000339807",
    "Outbound Team": "378942000000199401",
    "Business Analysts Team": "378942000007241305",
    "Project Management Team": "378942000028727416",
    "Brand Marketing": "378942000013754065",
    "Operations Team": "378942000009246025",
    "Development Contractors": "378942000026337117",
    "Partner's Devs": "378942000026337117",
    "Finance & Legal Department": "378942000030501276",
    "Development": "378942000026337117",
    "Delivery": "378942000028931765",
    "Talent Acquisition Department": "378942000000390015",
    "HR/Office Department": "378942000000349037"
}

RELEVANT_DEPARTMENTS = ["Development", "Partner's Devs", "Development Contractors", "Operations Team", "Operations Contractors", "Brand Marketing Team", 'Project Management Team', 'Business Analysts Team', 'Java Unit', 'Technology', 'QA Unit']

DEFAULT_PROJECTS_BY_BUDGET_OWNERS = {
    "Business Analysis": "378942000007241305",
    "CGT": "378942000030501302",
    "Client Development": "378942000000339807",
    "Development": "378942000026337117",
    "Finance Team": "378942000000530585",
    "HR/Office": "378942000000349037",
    "Java Unit": "378942000024070314",
    "Legal Team": "378942000030507278",
    "Marketing Team": "378942000013754065",
    "Operations Team": "378942000009246025",
    "Outbound Team": "378942000000199401",
    "Project Coordinators": "378942000000390047",
    "Project Management": "378942000028727416",
    "Recruiting Team": "378942000000390015",
    "Resource Management": "378942000028041920",
    "Unbench Team": "378942000000839114"
}


class LogSyncer:
    def __init__(self, start_date, end_date, custom_user_emails):
        self.start_date = start_date
        self.end_date = end_date
        self.search_start_date = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=2)).strftime('%Y-%m-%d')
        self.search_end_date = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
        self.start_date_unix = None
        self.end_date_unix = None
        self.custom_user_emails = custom_user_emails
        self.team_id = None
        self.clickup_users = []
        self.timezones_by_users = {}
        self.zp_employees = get_zp_employees()
        self.zp_projects = get_zp_projects()

    def get_all_clickup_users(self):
        response = requests.get("https://api.clickup.com/api/v2/team", headers=CLICKUP_HEADERS)
        team_data = response.json()['teams'][0]
        self.team_id = team_data['id']
        self.clickup_users = team_data['members']

    def get_timelogs(self, user_id):
        response = requests.get(f"https://api.clickup.com/api/v2/team/{self.team_id}/time_entries?assignee={user_id}&start_date={self.start_date_unix}&end_date={self.end_date_unix}", headers=CLICKUP_HEADERS)
        return response.json()['data'] if response.status_code == 200 else []

    def search_zp_user(self, email):
        for zp_employee in self.zp_employees:
            if zp_employee['email'] == email:
                return zp_employee

    def search_project_by_list_id(self, list_id):
        for zp_project in self.zp_projects:
            zp_project_details = list(zp_project.values())[0][0]
            if zp_project_details['Clickup_ID'] == list_id:
                return zp_project_details

    def search_project_by_project_id(self, project_id):
        for zp_project in self.zp_projects:
            zp_project_details = list(zp_project.values())[0][0]
            if str(zp_project_details['Zoho_ID']) == project_id:
                return zp_project_details

    def search_project_by_project_name(self, project_name):
        for zp_project in self.zp_projects:
            zp_project_details = list(zp_project.values())[0][0]
            if str(zp_project_details['Project_Name']) == project_name:
                return zp_project_details

    def get_billable_status(self, task_custom_fields):
        is_billable = True
        for task_custom_field in task_custom_fields:
            if task_custom_field['id'] == "ff1292a4-81ea-483e-8bae-9d13dff5d1c0" and 'value' in task_custom_field:
                if task_custom_field['value'] == 1:
                    is_billable = False
                    break
        return is_billable

    def user_handler(self, user):
        user_id = user['user']['id']
        user_email = user['user']['email']
        user_timelogs = self.get_timelogs(user_id)
        if not user_timelogs:
            return "No Timelogs Available"

        zp_user = self.search_zp_user(user_email)
        zp_user_department = zp_user['department']
        if zp_user_department not in RELEVANT_DEPARTMENTS:
            return "Irrelevant Department"

        zp_user_id = str(zp_user['id'])
        # GET LOGS FROM CLICKUP TO DELETE BEFORE PUSHING NEW ONCES
        current_zp_logs = get_zp_logs(user_email, self.start_date, self.end_date)
        current_zp_logs_to_delete = []
        for current_zp_log in current_zp_logs:
            try:
                log_check = int(current_zp_log['description'].replace("[bench]", ""))
                approval_status = current_zp_log['approvalStatus']
                #if approval_status in ['notsubmitted']:
                    #current_zp_logs_to_delete.append(current_zp_log['timelogId'])
                current_zp_logs_to_delete.append(current_zp_log['timelogId'])
            except:
                pass
        # user_timezone = get_timezone(user_id) or DEFAULT_TIMEZONE
        user_timezone = USER_TIMEZONES[user_email] if user_email in USER_TIMEZONES else DEFAULT_TIMEZONE
        print(f"\tUser Timezone: {user_timezone}")
        # self.timezones_by_users[user_email] = user_timezone
        # user_timezone = user_timezone or "Europe/Kyiv"
        # user_timezone = "Europe/Kyiv"
        total_tracked_hours = 0
        total_leave_hours = 0
        user_zp_timelogs = []
        history_by_task = {}

        clickup_tasks_details = {}

        total_time = 0
        time_by_projects = {}
        skipped_timelogs = 0
        jobs_created = 0
        for user_timelog in user_timelogs:
            # CONVERT LOG DATE TO USER TIMEZONE
            timelog_id = user_timelog['id']

            timelog_task = user_timelog['task'] if 'task' in user_timelog else {}
            if timelog_task == '0':
                return "Private Task available..."
            if not timelog_task:
                skipped_timelogs += 1
                continue
            timelog_task_type = timelog_task['custom_type']

            timelog_task_id = timelog_task['id']
            timelog_task_name = timelog_task['name']
            timelog_start_unix = int(user_timelog['start'])
            dt_utc = datetime.fromtimestamp(timelog_start_unix / 1000, tz=timezone.utc)
            dt_default_timezone = dt_utc.astimezone(pytz.timezone(DEFAULT_TIMEZONE))
            dt_user_timezone = dt_default_timezone.astimezone(pytz.timezone(user_timezone))
            timelog_date = dt_user_timezone.strftime('%Y-%m-%d')
            if str_to_date(self.start_date) <= str_to_date(timelog_date) <= str_to_date(self.end_date):
                # ALL GOOD, WE CAN CONTINUE
                pass
            else:
                continue
            timelog_duration = int(user_timelog['duration'])
            timelog_duration_hours = timelog_duration / (1000 * 60 * 60)

            # timelog_billable_status = user_timelog['billable']
            timelog_billable_status = False

            timelog_description = user_timelog['description']
            timelog_location = user_timelog['task_location']
            timelog_list_id = timelog_location['list_id']
            timelog_space_id = timelog_location['space_id']
            if timelog_list_id in LEAVES_LISTS:
                continue
            total_tracked_hours += timelog_duration_hours

            if timelog_task_id in clickup_tasks_details:
                clickup_task_details = clickup_tasks_details[timelog_task_id]
            else:
                clickup_task_details = get_clickup_task_by_id(timelog_task_id)

            # PROJECT CASES
            zp_project_id = None
            zp_project_data = None
            job_search_type = "by_user_input"
            job_search_name = None
            # CHECK IF TIMELOG IS IN HISTORY
            history_entity = {}
            if timelog_task_id in history_by_task:
                history_entity = history_by_task[timelog_task_id]
            elif timelog_space_id in COMMERCIAL_SPACES:
                zp_project_data = self.search_project_by_list_id(timelog_list_id)
                zp_project_id = str(zp_project_data['Zoho_ID'])
                job_search_type = "by_task_id"
            elif timelog_space_id in OUTSOURCE_SPACES:
                continue
            elif timelog_list_id in PRESALE_LISTS:
                try:
                    zp_project_id = str(self.search_project_by_project_name(timelog_task_name)['Zoho_ID'])
                except:
                    continue
                job_search_type = "by_job_name"
                job_search_name = "Presale Activities"
            elif timelog_list_id in INTERNAL_PROJECT_LISTS:
                zp_project_id = INTERNAL_PROJECT_LISTS[timelog_list_id]
                job_search_type = "by_task_id"
            # IN PROGRESS
            elif timelog_list_id in INTERNAL_ACTIVITIES_LISTS and timelog_task_type in INTERVIEW_TASK_TYPES:
                zp_project_id = "378942000015322402"
                job_search_type = "by_job_name"
                job_search_name = timelog_task_name
            elif timelog_list_id in INTERNAL_ACTIVITIES_LISTS and timelog_task_type in BENCH_TASK_TYPES:
                zp_project_id = "378942000004253148"
                job_search_type = "by_task_id"
            elif timelog_list_id in INTERNAL_ACTIVITIES_LISTS and timelog_task_type in PRESALE_TASK_TYPES:
                zp_project_id = "378942000023897482"
                # job_search_type = "by_task_id"
                job_search_type = "by_job_name"
                job_search_name = "Presale Activities"
            elif timelog_list_id in ADMIN_TASK_TRACKER_LISTS:
                budget_team_owner = None
                responsible_team = None
                custom_fields = clickup_task_details['custom_fields']
                for custom_field in custom_fields:
                    if custom_field['id'] == "7624aca5-8aeb-4eb0-8961-a72b78b2afbc" and 'value' in custom_field:
                        budget_team_owner = custom_field['value'][0]['name']
                    if custom_field['id'] == "c8658ab2-9e29-40bb-89f6-7e8d9d799d08" and 'value' in custom_field:
                        responsible_team = custom_field['value'][0]['name']
                if budget_team_owner and budget_team_owner in DEFAULT_PROJECTS_BY_BUDGET_OWNERS:
                    zp_project_id = DEFAULT_PROJECTS_BY_BUDGET_OWNERS[budget_team_owner]
                elif responsible_team and responsible_team in DEFAULT_PROJECTS_BY_BUDGET_OWNERS:
                    zp_project_id = DEFAULT_PROJECTS_BY_BUDGET_OWNERS[responsible_team]
                else:
                    if zp_user_department in DEFAULT_PROJECTS_BY_DEPARTMENT:
                        zp_project_id = DEFAULT_PROJECTS_BY_DEPARTMENT[zp_user_department]
                    else:
                        return "Unexpected Error"
                        zp_project_id = input(f"Please Provide Zoho People Project ID for task: {timelog_task_name}\nhttps://app.clickup.com/t/{timelog_task_id}:\n")
                job_search_type = "by_task_id"
            else:
                if zp_user_department in DEFAULT_PROJECTS_BY_DEPARTMENT:
                    zp_project_id = DEFAULT_PROJECTS_BY_DEPARTMENT[zp_user_department]
                else:
                    return "Unexpected Error"
                    zp_project_id = input(f"Please Provide Zoho People Project ID for task: {timelog_task_name}\nhttps://app.clickup.com/t/{timelog_task_id}:\n")
                job_search_type = "by_task_id"

            if not history_entity:
                if zp_project_id and not zp_project_data:
                    zp_project_data = self.search_project_by_project_id(zp_project_id)
                # ON THIS STAGE WE HAVE PROJECT ID AND PROJECT DETAILS
                # CHECK IF USER IS ASSIGNED TO A PROJECT
                print(f"\t\tChecking if user is assigned to project: {zp_project_id}")
                project_head = zp_project_data['ProjectHead.details']
                project_users = zp_project_data[
                    'ProjectUsers.details'] if 'ProjectUsers.details' in zp_project_data else []
                if user_email not in str(project_head) and user_email not in str(project_users):
                    print("\t\t\tUser Assigned to Project: False")
                    new_project_users = [x['erecno'] for x in project_users]
                    new_project_users.append(zp_user_id)
                    update_zp_project(zp_project_id, new_project_users)
                else:
                    print("\t\t\tUser Assigned to Project: True")

                # JOB CASES
                zp_job_data = None
                if job_search_type == "by_task_id":
                    zp_jobs_response = get_zp_job_by_clickup_id(timelog_task_id)
                    for zp_job_response in zp_jobs_response:
                        zp_job_details = zp_job_response[list(zp_job_response.keys())[0]][0]
                        zp_job_project_id = str(zp_job_details['Project.ID'])
                        if zp_job_project_id == zp_project_id:
                            zp_job_data = zp_job_details
                            break
                elif job_search_type == "by_job_name":
                    zp_jobs_response = get_zp_job_by_name(job_search_name)
                    for zp_job_response in zp_jobs_response:
                        zp_job_details = zp_job_response[list(zp_job_response.keys())[0]][0]
                        zp_job_project_id = str(zp_job_details['Project.ID'])
                        if zp_job_project_id == zp_project_id:
                            zp_job_data = zp_job_details
                            break
                elif job_search_type == "by_user_input":
                    return "Unexpected Error"
                    zp_job_id = input(
                        f"Please Provide Zoho People JOB ID for task: {timelog_task_name}\nhttps://app.clickup.com/t/{timelog_task_id}:\n")
                    # get zp_job_data by zp_job_id

                # CHECK JOB ASSIGNEES
                zp_job_id = None
                if zp_job_data:
                    zp_job_id = str(zp_job_data['Zoho_ID'])
                    job_assignee_ids = zp_job_details['Assignees.ID']
                    print(f"\t\tChecking is user is assigned to job {zp_job_id}")
                    if zp_user_id not in job_assignee_ids:
                        print("\t\t\tUser Assigned to Job: False")
                        job_assignees = job_assignee_ids.split(";")
                        job_assignees.append(zp_user_id)
                        update_zp_job(zp_job_id, job_assignees)
                    else:
                        print("\t\t\tUser Assigned to Job: True")
                else:
                    # CREATE A JOB
                    jobs_created += 1
                    print(f"\t\tCreating Zoho People Job {job_search_name or timelog_task_name}")
                    zp_job_id = create_zp_job(zp_project_id, timelog_task_id, job_search_name or timelog_task_name, [zp_user_id])
                # SAVE HISTORY
                history_by_task[timelog_task_id] = {"project_id": zp_project_id, "job_id": zp_job_id}
            else:
                zp_project_id = history_entity['project_id']
                zp_job_id = history_entity['job_id']

            if timelog_space_id in COMMERCIAL_SPACES or timelog_space_id in OUTSOURCE_SPACES:
                timelog_billable_status = self.get_billable_status(clickup_task_details['custom_fields'])

            zp_timelog_entry = {
                "user": user_email,
                "jobId": zp_job_id,
                "date": timelog_date,
                "billableStatus": "billable" if timelog_billable_status else "non-billable",
                "hours": format_hours(round(timelog_duration_hours, 2)),
                "workItem": timelog_description,
                "description": timelog_id,
            }
            if zp_project_id not in time_by_projects:
                time_by_projects[zp_project_id] = round(timelog_duration_hours, 2)
            else:
                time_by_projects[zp_project_id] += round(timelog_duration_hours, 2)

            user_zp_timelogs.append(zp_timelog_entry)
            total_time += round(timelog_duration_hours, 2)

        total_added = 0
        errors_detected = False
        if current_zp_logs_to_delete:
            print("\tDeleting Old Timelogs from Zoho People...")
            delete_message = delete_time_tracked(current_zp_logs_to_delete)
            if 'error' in delete_message.lower():
                errors_detected = True
            print(f"Delete Message: {delete_message}")
        print(f"Errors Detected in Deleting: {errors_detected}")
        if user_zp_timelogs and not errors_detected:
            print("\tPushing New Timelogs to Zoho People...")
            added_zp_timelogs = push_timelogs_to_zp(user_zp_timelogs)
            total_added = len(added_zp_timelogs)
        print(f"Total Jobs Created: {jobs_created}")
        return {"available_timelogs": len(user_zp_timelogs), "added_timelogs": total_added, "deleted_timelogs": len(current_zp_logs_to_delete) if not errors_detected else 0}

    def launcher(self):
        # ADD +- 2 DAYS TO AVOID TIMEZONE ISSUES
        print("Starting...")
        self.start_date_unix = datetime_str_to_unix(self.search_start_date, 0, 0)
        self.end_date_unix = datetime_str_to_unix(self.search_end_date, 23, 59)
        # GET ALL CLICKUP USERS
        print("Getting All Clickup Users...")
        self.get_all_clickup_users()
        counter = 0
        print(f"Total Clickup Users: {len(self.clickup_users)}")
        for user in self.clickup_users:
            user_email = user['user']['email']
            if self.custom_user_emails and user_email not in self.custom_user_emails:
                continue
            counter += 1
            print("------------" * 10)
            print(f"\t{counter}. Current User Email: {user_email}")
            time.sleep(1)
            # user_status = self.user_handler(user)
            try:
                user_status = self.user_handler(user)
            except Exception as e:
                print(e)
                user_status = None
            print(f"User Status: {user_status}")


def timelog_sync_launcher(start_date, end_date, users):
    logs_handler = LogSyncer(start_date, end_date, users)
    logs_handler.launcher()
    users_str = "All" if not users else ", ".join(users)
    send_slack_notification(SLACK_CHANNEL_TIMELOGS, f"Timelogs Sync from Clickup to Zoho People has been completed for *{users_str}* users")


