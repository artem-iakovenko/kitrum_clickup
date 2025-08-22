from scripts.help_functions import crm_get_records_from, get_zp_employees, get_working_days, get_clickup_users, clickup_get_tasks, datetime_str_to_unix, str_to_date, str_to_str_date, str_to_unix, get_list_custom_fields, get_cf_option_id, clickup_create_task
from .config import type_mapping, workload_mapping, current_mode, date_ranges
from secret_manager import access_secret

DEVELOPER_URL_CF_ID = "e6b5529b-167f-45f5-998c-cbeece722706"
DEVELOPER_INFO_URL_CF_ID = "7084b6d7-c48a-4288-b779-35731156b2fa"


CARD_TYPE_CF_ID = "cf215799-2435-4439-9c0e-0023ef93147e"
CARD_TYPE_CF_VALUES = {"Revenue Forecast": "ee05d33e-fba9-4e09-8649-8becfad40694", "New Start": "892872e7-150f-4cfa-becb-811c32ea6ee4"}


class ResourceBlocking:
    def __init__(self, custom_developer_info_id, date_range, card_type):
        self.clickup_headers = {"Content-Type": "application/json", "Authorization": access_secret('kitrum-cloud', "clickup")}
        self.custom_developer_info_id = custom_developer_info_id
        self.date_range = date_range
        self.card_type = card_type
        self.filter_start = str(datetime_str_to_unix(date_range['start'], 2, 0))
        self.filter_end = str(datetime_str_to_unix(date_range['end'], 22, 0))
        self.zp_employees = []
        self.all_developers = []
        self.all_potentials = []
        self.active_developers = []
        self.clickup_users = []
        self.month_resources = []
        self.month_blocks = []
        self.resource_cfs = []
        self.block_cfs = []

    def search_developer(self, developer_id):
        for developer in self.all_developers:
            if developer['id'] == developer_id:
                return developer

    def search_potential(self, potential_id):
        for potential in self.all_potentials:
            if potential['id'] == potential_id:
                return potential

    def search_zp_employee(self, developer_id):
        for zp_employee in self.zp_employees:
            if zp_employee['crm_id'] == developer_id:
                return zp_employee

    def search_clickup_user_by_email(self, user_email):
        for clickup_user in self.clickup_users:
            if clickup_user['user']['email'] == user_email:
                return clickup_user

    def search_resource(self, developer_id):
        for resource in self.month_resources:
            cfs = resource['custom_fields']
            for cf in cfs:
                if cf['id'] == DEVELOPER_URL_CF_ID and 'value' in cf:
                    if developer_id in cf['value']:
                        return resource

    def search_block(self, developer_info_id):
        for block in self.month_blocks:
            cfs = block['custom_fields']
            for cf in cfs:
                if cf['id'] == DEVELOPER_INFO_URL_CF_ID and 'value' in cf:
                    if developer_info_id in cf['value']:
                        return block

    def dev_info_hanlder(self, active_developer):
        dev_info_id = active_developer['id']
        dev_info_url = f"https://crm.zoho.com/crm/org55415226/tab/LinkingModule4/{dev_info_id}"
        if self.custom_developer_info_id and self.custom_developer_info_id != dev_info_id:
            return f"No need to create block for developer info {dev_info_url}"
        vendor_name = active_developer['Vendor_Name']['name']
        developer, potential = active_developer['Developers_on_project'], active_developer['Multi_Select_Lookup_1']
        developer_status = active_developer['Status']

        developer_id, potential_id = developer['id'], potential['id']
        developer_name = developer['name']
        developer_url = f"https://crm.zoho.com/crm/org55415226/tab/CustomModule1/{developer_id}"
        resource = self.search_resource(developer_id)
        block = self.search_block(dev_info_id)
        if block:
            return f"Block already Exist for developer info {dev_info_url}"
        zp_employee_details = self.search_zp_employee(developer_id)

        terms_of_work = zp_employee_details['terms'] if zp_employee_details else None
        developer_email = zp_employee_details['email'] if zp_employee_details else None
        developer_clickup_user = self.search_clickup_user_by_email(developer_email) if developer_email else None
        developer_clickup_user_id = developer_clickup_user['user']['id'] if developer_clickup_user else None
        print(f"Developer Clickup ID: {developer_clickup_user_id}")
        developer_details = self.search_developer(developer_id)

        potential_details = self.search_potential(potential_id)
        project_clickup_id = potential_details['ClickUp_ID']
        type_of_member = developer_details['Type_of_member']
        hpd = 8
        if developer_id in ['1576533000099422137']:
            hpd = 6
        seniority = developer_details["Seniority"]
        direction = developer_details["Direction"]
        title = developer_details["Title"]
        potential_delivery = potential_details['Potential_Delivery_Owner']
        workload = active_developer['Workload']
        estimated_hours = active_developer['Number_of_hours'] or 0
        start_on_project = active_developer['Start_Date_on_Project']
        end_on_project = active_developer['Final_Date_on_Project']
        # end_on_project = '2025-08-17'
        if end_on_project and str_to_date(end_on_project) < str_to_date(self.date_range['start']):
            return "Finished before current date range. No Need to Create"

        range_start_date, range_end_date = self.date_range['start'], self.date_range['end']
        if potential_id == "1576533000386486133":
            project_manager_email = "valia@kitrum.com"
        else:
            project_manager_email = f'{potential_delivery.replace(" ", ".")}@kitrum.com'.lower() if potential_delivery else None
        project_manager_clickup_user = self.search_clickup_user_by_email(project_manager_email)
        project_manager_clickup_user_id = project_manager_clickup_user['user']['id'] if project_manager_clickup_user else None

        # COLLECT RESOURCE DATA
        start_at_kitrum = zp_employee_details['joining_date'] if zp_employee_details and 'joining_date' in zp_employee_details else None
        end_at_kitrum = zp_employee_details['exit_date'] if zp_employee_details and 'exit_date' in zp_employee_details else None
        print(f"KITRUM: {start_at_kitrum} - {end_at_kitrum or 'present'}")
        resource_start_date = self.date_range['start']
        resource_end_date = self.date_range['end']

        if start_at_kitrum:
            if str_to_date(start_at_kitrum) > str_to_date(self.date_range['start']) and str_to_date(start_at_kitrum) < str_to_date(self.date_range['end']):
                resource_start_date = start_at_kitrum
        if end_at_kitrum:
            # if str_to_date(end_at_kitrum) < str_to_date(self.date_range['start']):
            #     return "Developer already finished cooperation with KITRUM"
            if str_to_date(end_at_kitrum) > str_to_date(self.date_range['start']) and str_to_date(end_at_kitrum) < str_to_date(self.date_range['end']):
                resource_end_date = end_at_kitrum
        resource_hours = get_working_days(resource_start_date, resource_end_date) * hpd
        clickup_resource_custom_fields = [
            {"id": "912a953f-4c89-44cb-844d-603111aa7eb1", "value": {"add": [developer_clickup_user_id], "rem": []}},
            {"id": "031efcab-a89c-4f7f-bb03-208b209943a9", "value": type_mapping[type_of_member]},
            {"id": "3fac0ff8-6981-463a-b7e0-a375f86aed24", "value": str(resource_hours)},
            {"id": "e6b5529b-167f-45f5-998c-cbeece722706", "value": developer_url},
            {"id": "66c97dab-0d09-4dc2-9416-ae666a6e6d42", "value": workload_mapping[terms_of_work] if terms_of_work else None},
        ]
        seniority_option_id = get_cf_option_id(self.clickup_headers, self.resource_cfs, "006faef7-4e5a-41c7-8b54-a8ed2665bb70", seniority)
        if seniority_option_id:
            clickup_resource_custom_fields.append({"id": "006faef7-4e5a-41c7-8b54-a8ed2665bb70", "value": seniority_option_id})
        direction_option_id = get_cf_option_id(self.clickup_headers, self.resource_cfs, "baf5146f-534c-44e0-9b9d-f84329154369", direction)
        if direction_option_id:
            clickup_resource_custom_fields.append({"id": "baf5146f-534c-44e0-9b9d-f84329154369", "value": direction_option_id})
        title_option_id = get_cf_option_id(self.clickup_headers, self.resource_cfs, "33cc9332-2bda-43e3-97fc-1131c8a0d5ee", title)
        if title_option_id:
            clickup_resource_custom_fields.append({"id": "33cc9332-2bda-43e3-97fc-1131c8a0d5ee", "value": title_option_id})

        clickup_resource_data = {
            "name": f"{developer_name} - {str_to_str_date(self.date_range['end'])}",
            "status": "work on project",
            "start_date": str_to_unix(self.date_range['start']),
            "due_date": str_to_unix(self.date_range['end']),
            "custom_item_id": 1001,
            "custom_fields": clickup_resource_custom_fields
        }
        if not resource:
            resource = clickup_create_task(self.clickup_headers, "901204930768", clickup_resource_data)
            self.month_resources.append(resource)

        resource_id = resource['id']

        # COLLECT BLOCK DATA
        blocking_name = f"{developer['name']} - {potential['name']}"
        blocking_start_date = self.date_range['start']
        blocking_end_date = self.date_range['end']
        if start_on_project:
            if str_to_date(start_on_project) > str_to_date(self.date_range['start']) and str_to_date(start_on_project) < str_to_date(self.date_range['end']):
                blocking_start_date = start_on_project
        if end_on_project:
            if str_to_date(end_on_project) < str_to_date(self.date_range['start']):
                print(f"Developer is Inactive on the project {dev_info_url}")
            if str_to_date(end_on_project) > str_to_date(self.date_range['start']) and str_to_date(end_on_project) < str_to_date(self.date_range['end']):
                blocking_end_date = end_on_project

        blocking_hours = 0
        available_hours = 0
        if workload == "Full-time":
            blocking_hours = get_working_days(blocking_start_date, blocking_end_date) * 8 if developer_status != "OnHold" else 0
            available_hours = get_working_days(blocking_start_date, blocking_end_date) * 8
        else:
            if estimated_hours <= 0:
                return f"Estimated hours in empty on developer info: {dev_info_url}"
            blocking_hours = estimated_hours if developer_status != "OnHold" else 0
            available_hours = estimated_hours

        clickup_blocking_custom_fields = [
            {"id": "031efcab-a89c-4f7f-bb03-208b209943a9", "value": type_mapping[type_of_member]},
            {"id": "66c97dab-0d09-4dc2-9416-ae666a6e6d42", "value": workload_mapping[workload]},
            {"id": "912a953f-4c89-44cb-844d-603111aa7eb1", "value": {"add": [developer_clickup_user_id], "rem": []}},
            {"id": "6400cee4-b94c-45a0-ac67-02ec18770c8e", "value": {"add": [project_manager_clickup_user_id], "rem": []}},
            {"id": "5078d821-4695-4e09-ae6c-81e29081ef66", "value": str(blocking_hours)},
            {"id": "9a832c69-edab-40eb-a81d-03be6078b0d9", "value": str(available_hours)},
            {"id": "e3b6c6ea-c8a4-4318-90f8-168f6b54307e", "value": {"add": [resource_id], "rem": []}},
            {"id": "7f3b4b79-b252-42ea-83fc-8c59445148f9", "value": {"add": [project_clickup_id], "rem": []}},
            {"id": "7084b6d7-c48a-4288-b779-35731156b2fa", "value": dev_info_url},
            {"id": "cf215799-2435-4439-9c0e-0023ef93147e", "value": CARD_TYPE_CF_VALUES[self.card_type]}
        ]
        if seniority_option_id:
            clickup_blocking_custom_fields.append(
                {"id": "006faef7-4e5a-41c7-8b54-a8ed2665bb70", "value": seniority_option_id})
        if direction_option_id:
            clickup_blocking_custom_fields.append(
                {"id": "baf5146f-534c-44e0-9b9d-f84329154369", "value": direction_option_id})
        if title_option_id:
            clickup_blocking_custom_fields.append(
                {"id": "33cc9332-2bda-43e3-97fc-1131c8a0d5ee", "value": title_option_id})

        blocking_status = 'in progress'
        if developer_status in ['OnHold']:
            blocking_status = 'on hold'
        clickup_blocking_data = {
            "name": blocking_name,
            "status": blocking_status,
            "start_date": str_to_unix(blocking_start_date),
            "due_date": str_to_unix(blocking_end_date),
            "custom_item_id": 1006,
            "custom_fields": clickup_blocking_custom_fields
        }
        blocking = clickup_create_task(self.clickup_headers, "901204980269", clickup_blocking_data)
        self.month_blocks.append(blocking)
        blocking_id = blocking['id']
        return blocking_id

    def launcher(self):
        self.resource_cfs = get_list_custom_fields(self.clickup_headers, "901204930768")
        self.block_cfs = get_list_custom_fields(self.clickup_headers, "901204980269")
        self.month_resources = clickup_get_tasks(self.clickup_headers, "901204930768", f"&include_closed=true&due_date_lt={self.filter_end}&due_date_gt={self.filter_start}")
        print(f"Total Resources Exist in Range: {len(self.month_resources)}")
        self.month_blocks = clickup_get_tasks(self.clickup_headers, "901204980269", f"&include_closed=true&due_date_lt={self.filter_end}&due_date_gt={self.filter_start}")
        print(f"Total Blocks Exist in Range: {len(self.month_blocks)}")
        self.clickup_users = get_clickup_users(self.clickup_headers)
        self.zp_employees = get_zp_employees()
        print(f"Total Zoho People Employees Fetched: {len(self.zp_employees)}")
        self.all_developers = crm_get_records_from("Developers", None)
        print(f"Total Zoho CRM Developers Fetched: {len(self.all_developers)}")
        self.all_potentials = crm_get_records_from("Deals", None)
        print(f"Total Zoho CRM Potentials Fetched: {len(self.all_potentials)}")
        self.active_developers = crm_get_records_from("Project_Details", "1576533000362341337")
        print(f"Total Zoho CRM Active Dev Infos Fetched: {len(self.active_developers)}")
        counter = 0
        for active_developer in self.active_developers:
            counter += 1
            print("------------------")
            print(f"{counter}/{len(self.active_developers)}. Current Developer info: {active_developer['id']}")
            result = self.dev_info_hanlder(active_developer)
            print(f"\tResult: {result}")


# date_ranges = [{"start": '2025-07-01', "end": '2025-07-31'}, {"start": '2025-08-01', "end": '2025-08-31'}, {"start": '2025-09-01', "end": '2025-09-30'}]
# QUARTERLY FORECAST
# for date_range in date_ranges:
#     resource_blocking_handler = ResourceBlocking(None", date_range, "Quarterly Forecast")
#     resource_blocking_handler.launcher()

# date_ranges = [{"start": '2025-06-01', "end": '2025-06-30'}]
# date_ranges = [{"start": '2025-07-01', "end": '2025-07-31'}, {"start": '2025-08-01', "end": '2025-08-31'}, {"start": '2025-09-01', "end": '2025-09-30'}]

# NEW START
def launch_creator(dev_info_id):
    for date_range in date_ranges:
        resource_blocking_handler = ResourceBlocking(dev_info_id, date_range, current_mode)
        resource_blocking_handler.launcher()
