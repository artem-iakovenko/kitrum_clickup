import time
from _datetime import datetime, timedelta
import numpy as np
from zoho_api.api import api_request
import re
from credentials.api_creds import CLICKUP_HEADERS, SLACK_HEADRES
import requests
import json


def get_timelogs(start_date, end_date):
    all_timelogs = []
    s_index = 1
    while True:
        print(f"\tCurrent Index: {s_index}")
        try:
            page_response = api_request(
                f"https://people.zoho.com/people/api/timetracker/gettimelogs?user=all&jobId=all&fromDate={start_date}&toDate={end_date}&billingStatus=all&sIndex={s_index}&limit=200",
                "zoho_people",
                "get",
                None
            )['response']['result']
        except:
            break
        if len(page_response) == 0:
            break
        all_timelogs.extend(page_response)
        s_index += 200
    return all_timelogs


def check_if_date_in_range(date_to_check, range_start, range_end):
    if not date_to_check:
        return False
    if str_to_date(date_to_check) >= str_to_date(range_start) and str_to_date(date_to_check) <= str_to_date(range_end):
        return True
    return False


def get_slack_channel_members(channel_id):
    response = requests.get(f"https://slack.com/api/conversations.members?channel={channel_id}", headers=SLACK_HEADRES)
    return {"status": response.status_code, "json": response.json()}

def send_slack_notification(channel_id, notification_text):
    post_data = {"channel": channel_id, "text": notification_text};
    response = requests.post("https://slack.com/api/chat.postMessage", headers=SLACK_HEADRES, json=post_data)
    return {"status": response.status_code, "json": response.json()}


def batch_generator(data, batch_size=100):
    for i in range(0, len(data), batch_size):
        yield data[i:i + batch_size]


def delete_time_tracked(timelog_ids):
    response = requests.post("https://www.zohoapis.com/crm/v7/functions/delete_bulk_timelogs/actions/execute?auth_type=apikey&zapikey=1003.4dc6e131901e2b9c2dc52b73bc81a5ad.b66d89f85e0370bb8fb7ba2a082271de", json={"timelogs": timelog_ids})
    status_code = response.status_code
    try:
        output = response.json()['details']['output']
        output_message = json.loads(output)['response']['message']
    except:
        output_message = "No message"
    print(f"\tDeleting Time Logs Status: {status_code}")
    return output_message


def push_timelogs_to_zp(timelogs):
    # print(f"Total Timelogs to Push: {len(timelogs)}")
    batch_counter = 0
    timelogs_added = []
    for logs_batch in batch_generator(timelogs):
        batch_counter += 1
        # print(f"Batch: {batch_counter}")
        batch_post_data = {"timelogs": logs_batch}
        response = requests.post(
            "https://www.zohoapis.com/crm/v7/functions/addbulktimelogs/actions/execute?auth_type=apikey&zapikey=1003.4dc6e131901e2b9c2dc52b73bc81a5ad.b66d89f85e0370bb8fb7ba2a082271de",
            json=batch_post_data
        )
        output = response.json()['details']['output']
        try:
            batch_added = json.loads(output)['response']['result']['addedTimelogIds']
        except:
            batch_added = []

        timelogs_added.extend(batch_added)
    return timelogs_added


def get_zp_logs(user_email, start_date, end_date):
    s_index = 1
    user_zp_logs = []
    while True:
        try:
            page_logs = api_request(
                f"https://people.zoho.com/people/api/timetracker/gettimelogs?fromDate={start_date}&toDate={end_date}&billingStatus=all&user={user_email}&sIndex={s_index}&limit=200",
                "zoho_people",
                "get",
                None
            )['response']['result']
        except KeyError:
            page_logs = []
        if not page_logs:
            break
        user_zp_logs.extend(page_logs)
        s_index += 200
    return user_zp_logs


def clickup_update_task_data(task_id, task_data):
    response = requests.put(
        f"https://api.clickup.com/api/v2/task/{task_id}",
        headers=CLICKUP_HEADERS,
        json=task_data
    )
    return {"status": response.status_code, "data": response.json()}


def clickup_update_cf(task_id, cf_id, cf_value):
    response = requests.post(f"https://api.clickup.com/api/v2/task/{task_id}/field/{cf_id}", headers=CLICKUP_HEADERS, json={"value": cf_value})
    return {"status": response.status_code, "data": response.json()}


def clickup_create_task(list_id, task_data):
    response = requests.post(f"https://api.clickup.com/api/v2/list/{list_id}/task", headers=CLICKUP_HEADERS,
                             json=task_data)
    return response.json()


def get_cf_option_id(custom_fields, custom_field_id, search_value):
    for custom_field in custom_fields:
        try:
            if custom_field['id'] != custom_field_id:
                continue
            custom_field_options = custom_field['type_config']['options']
            for custom_field_option in custom_field_options:
                if custom_field_option['name'] == search_value:
                    return custom_field_option['id']
        except:
            pass
    return None

def get_list_custom_fields(list_id):
    response = requests.get("https://api.clickup.com/api/v2/list/" + list_id + "/field", headers=CLICKUP_HEADERS)
    return response.json()['fields']


def get_clickup_task_by_id(task_id):
    response = requests.get(f"https://api.clickup.com/api/v2/task/{task_id}?include_subtasks=true", headers=CLICKUP_HEADERS)
    return response.json()

def clickup_get_tasks(list_id, additional_params):
    page = 0
    all_tasks = []
    while True:
        resources_response = requests.get(
            f'https://api.clickup.com/api/v2/list/{list_id}/task?page={page}{additional_params or ""}',
            headers=CLICKUP_HEADERS)
        page += 1
        if len(resources_response.json()['tasks']) == 0:
            break
        print(len(resources_response.json()['tasks']))
        all_tasks.extend(resources_response.json()['tasks'])
    return all_tasks


def get_clickup_users():
    response = requests.get("https://api.clickup.com/api/v2/team/", headers=CLICKUP_HEADERS)
    return response.json()['teams'][0]['members']

def crm_get_records_from(module_name, cv_id):
    page = 0
    cv_records = []
    additional_params = f"&cvid={cv_id}" if cv_id else ""
    while True:
        page += 1
        try:
            page_data = api_request(
                f"https://www.zohoapis.com/crm/v2/{module_name}?page={page}{additional_params}",
                "zoho_crm",
                "get",
                None
            )['data']
            cv_records.extend(page_data)
        except:
            break
    return cv_records


def crm_get_records_by_id(module_name, record_id):
    try:
        response = api_request(
            f"https://www.zohoapis.com/crm/v2/{module_name}/{record_id}",
            "zoho_crm",
            "get",
            None
        )['data'][0]
    except:
        response = None
    return response


def prettify_task_name(task_name):
    prettified_name = re.sub(r'[^a-zA-Z0-9 \-]', '', task_name)
    prettified_name = re.sub(r'\s+', ' ', prettified_name).strip()
    if len(prettified_name) > 90:
        return f"{prettified_name[0:85]}..."
    else:
        return prettified_name


def update_zp_project(project_id, new_project_users):
    update_project = api_request(
        "https://people.zoho.com/people/api/forms/json/P_TimesheetJobsList/updateRecord?inputData={ProjectUsers:'" + ';'.join(
            new_project_users) + "'}&recordId=" + project_id,
        "zoho_people",
        "post",
        None
    )
    print(f"\t\tProject Update: {update_project['response']['message']}")


def create_zp_job(project_id, task_id, job_name, job_assignees):
    response = api_request(
        "https://people.zoho.com/people/api/forms/json/P_TimesheetJob/insertRecord?inputData={Job_Name:'" + prettify_task_name(
            job_name) + "',Project:'" + project_id + "',Assignees:'" + ';'.join(
            job_assignees) + "',Clickup_ID:'" + task_id + "'}",
        "zoho_people",
        "post",
        None
    )
    print(f"\t\tCreate Job: {response['response']['message']}")
    return response['response']['result']['pkId']


# def get_zp_employees():
#     s_index = 1
#     all_employees = []
#     while True:
#         try:
#             page_employees = api_request(
#                 "https://people.zoho.com/people/api/forms/employee/getRecords?sIndex=" + str(
#                     s_index) + "&searchParams={searchField: 'Employeestatus', searchOperator: 'Is', searchText : 'Active'}",
#                 "zoho_people",
#                 "get",
#                 None
#             )['response']['result']
#         except KeyError:
#             break
#         for page_employee in page_employees:
#             zp_employee_id = list(page_employee.keys())[0]
#             zp_employee_data = page_employee[zp_employee_id][0]
#             all_employees.append({"email": zp_employee_data['EmailID'], 'id': str(zp_employee_data['Zoho_ID']),
#                                       'name': f'{zp_employee_data["FirstName"]} {zp_employee_data["LastName"]}',
#                                       'short_id': zp_employee_data['EmployeeID'],
#                                       "crm_id": zp_employee_data['CRM_Developer_ID']})
#         s_index += 200
#     return all_employees


def update_zp_job(job_id, job_assignees):
    update_job = api_request(
        "https://people.zoho.com/people/api/forms/json/P_TimesheetJob/updateRecord?inputData={Assignees:'" + ';'.join(
            job_assignees) + "'}&recordId=" + str(job_id),
        "zoho_people",
        "post",
        None
    )
    print(f"\t\tUpdate Job: {update_job['response']['message']}")


def get_zp_job_by_clickup_id(clickup_task_id):
    try:
        zp_job = api_request(
            "https://people.zoho.com/people/api/forms/P_TimesheetJob/getRecords?sIndex=1&rec_limit=200&searchParams={searchField: 'Clickup_ID', searchOperator: 'Is', searchText : '" + clickup_task_id + "'}",
            "zoho_people", "get", None)['response']['result']
    except KeyError:
        zp_job = []
    return zp_job


def get_zp_job_by_name(job_name):
    try:
        zp_job = api_request(
            "https://people.zoho.com/people/api/forms/P_TimesheetJob/getRecords?sIndex=1&rec_limit=200&searchParams={searchField: 'Job_Name', searchOperator: 'Is', searchText : '" + job_name + "'}",
            "zoho_people", "get", None)['response']['result']
    except KeyError:
        zp_job = []
    return zp_job


def get_zp_projects():
    s_index = 1
    all_projects = []
    while True:
        try:
            response = api_request(
                f"https://people.zoho.com/people/api/forms/P_TimesheetJobsList/getRecords?sIndex={s_index}&limit=200",
                "zoho_people",
                "get",
                None
            )['response']['result']
        except KeyError:
            response = []
        if not response:
            break
        all_projects.extend(response)
        s_index += 200
    return all_projects


def unix_to_date(ts_value):
    try:
        unix_timestamp_sec = (int(ts_value) + 3600000) / 1000
        date = datetime.fromtimestamp(unix_timestamp_sec)
        return date.strftime('%Y-%m-%d')
    except Exception as e:
        print(e)
        print('oshibkus')
        return None

def format_hours(hours):
    h = int(hours)
    m = int(round(round(hours - h, 2) * 60, 0))
    return f"{h}:{m:02}"

def str_to_date(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d").date()


def datetime_str_to_unix(date_string, hours, minutes):
    if not date_string:
        return ""
    date_obj = datetime.strptime(date_string, "%Y-%m-%d")
    date_obj = date_obj.replace(hour=hours, minute=minutes, second=0)
    #gmt_plus_2 = pytz.timezone("Etc/GMT+2")
    #date_obj_gmt_plus_2 = gmt_plus_2.localize(date_obj)
    unix_timestamp = int(date_obj.timestamp()) * 1000
    return unix_timestamp


def str_to_datetime(date_string):
    return datetime.strptime(date_string, "%Y-%m-%d")


def str_to_unix(date_string):
    return int(str_to_datetime(date_string).timestamp() * 1000)


def str_to_str_date(date_string):
    date_obj = str_to_date(date_string)
    return date_obj.strftime("%B %Y")


def get_working_days(start, end):
    return np.busday_count(str_to_date(start), str_to_date(end) + timedelta(days=1))


def get_zp_all_employees():
    s_index = 1
    result = []
    while True:
        try:
            page_employees = api_request(
                "https://people.zoho.com/people/api/forms/employee/getRecords?sIndex=" + str(
                    s_index),
                "zoho_people",
                "get",
                None
            )['response']['result']
        except KeyError:
            break
        for page_employee in page_employees:
            zp_employee_id = list(page_employee.keys())[0]
            zp_employee_data = page_employee[zp_employee_id][0]
            # result.append({"joining_date": zp_employee_data['Dateofjoining'], "exit_date": zp_employee_data["Dateofexit"], "terms": zp_employee_data['Terms_of_work'], "crm_id": zp_employee_data['CRM_Developer_ID'], "email": zp_employee_data['EmailID'], "department": zp_employee_data['Department'], 'id': zp_employee_data['Zoho_ID'], 'name': f'{zp_employee_data["FirstName"]} {zp_employee_data["LastName"]}', "team": zp_employee_data["Team"], "staff_type": zp_employee_data["Staff_type"], 'short_id': zp_employee_data['EmployeeID']})
            result.append({"joining_date": zp_employee_data['Dateofjoining'], "exit_date": zp_employee_data["Dateofexit"],
                       "terms": zp_employee_data['Terms_of_work'], "crm_id": zp_employee_data['CRM_Developer_ID'],
                       "email": zp_employee_data['EmailID'], "department": zp_employee_data['Department'],
                       'id': zp_employee_data['Zoho_ID'],
                       'name': f'{zp_employee_data["FirstName"]} {zp_employee_data["LastName"]}',
                       "team": zp_employee_data["Team"], "staff_type": zp_employee_data["Staff_type"],
                       'short_id': zp_employee_data['EmployeeID'], "employee_type": zp_employee_data['Employee_type']})

        s_index += 200
    return result


def get_zp_employees():
    s_index = 1
    result = []
    while True:
        try:
            page_employees = api_request(
                "https://people.zoho.com/people/api/forms/employee/getRecords?sIndex=" + str(
                    s_index) + "&searchParams={searchField: 'Employeestatus', searchOperator: 'Is', searchText : 'Active'}",
                "zoho_people",
                "get",
                None
            )['response']['result']
        except KeyError:
            break
        for page_employee in page_employees:
            zp_employee_id = list(page_employee.keys())[0]
            zp_employee_data = page_employee[zp_employee_id][0]
            result.append({"joining_date": zp_employee_data['Dateofjoining'], "exit_date": zp_employee_data["Dateofexit"], "terms": zp_employee_data['Terms_of_work'], "crm_id": zp_employee_data['CRM_Developer_ID'], "email": zp_employee_data['EmailID'], "department": zp_employee_data['Department'], 'id': zp_employee_data['Zoho_ID'], 'name': f'{zp_employee_data["FirstName"]} {zp_employee_data["LastName"]}', "team": zp_employee_data["Team"], "staff_type": zp_employee_data["Staff_type"], 'short_id': zp_employee_data['EmployeeID']})
        s_index += 200
    return result