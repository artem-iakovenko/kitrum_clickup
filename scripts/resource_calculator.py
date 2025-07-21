
from scripts.help_functions import str_to_unix, datetime_str_to_unix, str_to_date, get_working_days, clickup_get_tasks, get_zp_employees, get_zp_all_employees, get_clickup_users, crm_get_records_from, get_clickup_task_by_id, crm_get_records_by_id, clickup_update_cf, clickup_update_task_data, check_if_date_in_range
from datetime import datetime
from .config import date_ranges

INTERNAL_TASKS = []

class ResourceCalculation:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.filter_start = str(datetime_str_to_unix(start_date, 2, 0)) if start_date else None
        self.filter_end = str(datetime_str_to_unix(end_date, 22, 0)) if end_date else None
        self.month_resources = []
        self.month_blocks = []
        self.month_leaves = []
        self.active_dev_infos = []
        self.potentials = []
        self.developers = {}
        self.clickup_users = []
        self.zp_employees = []

    def get_zp_data_by_crm_id(self, crm_id):
        for zp_employee in self.zp_employees:
            if zp_employee['crm_id'] == crm_id:
                return zp_employee

    def get_potential(self, potential_id):
        for potential in self.potentials:
            if potential['id'] == potential_id:
                return potential

    def get_developer(self, developer_id):
        if developer_id in self.developers:
            return self.developers[developer_id]
        response = crm_get_records_by_id(developer_id)
        if response:
            self.developers[developer_id] = response
            return response

    def get_leave_details(self, leave_id):
        for leave in self.month_leaves:
            if leave['id'] == leave_id:
                return leave

    def get_block_details(self, block_id):
        for block in self.month_blocks:
            if block['id'] == block_id:
                return block

    def get_dev_info_details(self, dev_info_id):
        for dev_info in self.active_dev_infos:
            if dev_info['id'] == dev_info_id:
                return dev_info

    def launch(self):
        self.clickup_users = get_clickup_users()
        self.zp_employees = get_zp_all_employees()
        self.potentials = crm_get_records_from("Deals", None)
        self.month_blocks = clickup_get_tasks("901204980269", f"&include_closed=true&due_date_lt={self.filter_end}&due_date_gt={self.filter_start}")
        self.month_leaves = clickup_get_tasks("901204775879", f"&include_closed=true&due_date_lt={self.filter_end}&due_date_gt={self.filter_start}")
        self.active_dev_infos = crm_get_records_from("Project_Details", "1576533000362341337")
        internal_project = get_clickup_task_by_id("869775k91")
        internal_task_ids = ["8696eea8p", "869775k91", "869775k91"]
        internal_project_subtasks = internal_project['subtasks'] if 'subtasks' in internal_project else []
        for internal_project_subtask in internal_project_subtasks:
            internal_task_ids.append(internal_project_subtask['id'])
        self.month_resources = clickup_get_tasks("901204930768", f"&include_closed=true&due_date_lt={self.filter_end}&due_date_gt={self.filter_start}")
        counter = 0
        for resource in self.month_resources:
            counter += 1
            print("-------" * 20)
            resource_id = resource['id']
            #
            # if resource_id != "8699f5dd5":
            #     continue

            print(f"{counter}/{len(self.month_resources)}. Resource Name: {resource['name']} - {resource_id}")

            # GET LEAVE AND BLOCKING TASK IDS
            custom_fields = resource['custom_fields']
            leave_task_ids = []
            blocking_task_ids = []
            developer_url, resource_current_developer_id = None, None

            resource_total_blocked = 0
            resource_total_available = 0
            resource_commercial_hours = 0
            resource_internal_hours = 0
            current_free_hours = 0
            current_utilization = 0
            for custom_field in custom_fields:
                if custom_field['id'] == "3fac0ff8-6981-463a-b7e0-a375f86aed24" and 'value' in custom_field:
                    resource_total_available = round(float(custom_field['value']), 2)
                elif custom_field['id'] == "e3b6c6ea-c8a4-4318-90f8-168f6b54307e" and 'value' in custom_field:
                    for blocking_task in custom_field['value']:
                        blocking_task_ids.append(blocking_task['id'])
                elif custom_field['id'] == "9f9c873c-dea9-4f61-b427-00e92038e756" and 'value' in custom_field:
                    for leave_task in custom_field['value']:
                        leave_task_ids.append(leave_task['id'])
                elif custom_field['id'] == "e6b5529b-167f-45f5-998c-cbeece722706" and 'value' in custom_field:
                    developer_url = custom_field['value']
                elif custom_field['id'] == "912a953f-4c89-44cb-844d-603111aa7eb1" and 'value' in custom_field:
                    resource_current_developer_id = custom_field['value'][0]['id'] if custom_field['value'] else None
                elif custom_field['id'] == "cf0b9445-8383-4d93-bc56-52a2c2c551b7" and 'value' in custom_field:
                    current_free_hours = round(float(custom_field['value']), 2)
                elif custom_field['id'] == "703dd683-1188-4427-a1a3-205733badd3f" and 'value' in custom_field:
                    current_utilization = round(float(custom_field['value']), 2)

            dev_id = None
            if developer_url:
                try:
                    dev_id = developer_url.split("?")[0].split("/")[-1]
                except Exception as e:
                    print(e)
                    dev_id = None

            hpd = 8
            if dev_id in ['1576533000099422137']:
                hpd = 6

            zp_employee_data = self.get_zp_data_by_crm_id(dev_id)

            print(f"ZP EMPLOYEE AVAILABLE: {True if zp_employee_data else False}")
            kitrum_joining_date = zp_employee_data['joining_date'] if zp_employee_data else None
            kitrum_exit_date = None
            print(zp_employee_data)
            if 'contractor' not in zp_employee_data['employee_type'].lower():
                kitrum_exit_date = zp_employee_data['exit_date'] if zp_employee_data else None
            exited_before_this_month = False
            if kitrum_exit_date and str_to_date(kitrum_exit_date) < str_to_date(self.start_date):
                print(kitrum_exit_date)
                print(f"EXITED BEFORE MONTH START")
                print("CHANGE MONTH HOURS TO 0")
                exited_before_this_month = True
            print(f"Exited before this month: {exited_before_this_month}")

            resource_start_date = kitrum_joining_date if kitrum_joining_date and check_if_date_in_range(kitrum_joining_date, self.start_date, self.end_date) else self.start_date
            resource_end_date = kitrum_exit_date if kitrum_exit_date and check_if_date_in_range(kitrum_exit_date, self.start_date, self.end_date) else self.end_date
            new_resource_total_available = resource_total_available
            print(f"Resource Available hours: {new_resource_total_available}")
            print(f"Resource Relevant Range: {resource_start_date} - {resource_end_date}")

            if resource_start_date != self.start_date or resource_end_date != self.end_date:
                new_resource_total_available = get_working_days(resource_start_date, resource_end_date) * hpd
            elif exited_before_this_month:
                new_resource_total_available = 0

            terms_of_work = zp_employee_data['terms'] if zp_employee_data else None

            # input(f"Terms of Work: {terms_of_work}")
            dev_email = zp_employee_data['email'] if zp_employee_data else None

            clickup_developer_id = ""
            for clickup_user in self.clickup_users:
                if dev_email == clickup_user['user']['email']:
                    clickup_developer_id = clickup_user['user']['id']
                if clickup_developer_id:
                    break

            # GET RESOURCE LEAVE HOURS
            leave_hours = 0
            total_planned_leave_hours = 0
            for leave_task_id in leave_task_ids:
                leave_data = self.get_leave_details(leave_task_id)
                if not leave_data:
                    leave_data = get_clickup_task_by_id(leave_task_id)
                for custom_field in leave_data['custom_fields']:
                    if custom_field['id'] == "5078d821-4695-4e09-ae6c-81e29081ef66":
                        leave_hours += round(float(custom_field['value']), 2)

            # CALCULATE BLOCKINGS
            print(f"Total Blocks Available: {len(blocking_task_ids)}\n")
            for blocking_task_id in blocking_task_ids:
                blocking_data = self.get_block_details(blocking_task_id)
                print(f"\tBlocking Name: {blocking_data['name']}")

                if not blocking_data:
                    blocking_data = get_clickup_task_by_id(blocking_task_id)
                start_date_unix = int(blocking_data['start_date'])
                due_date_unix = int(blocking_data['due_date'])

                current_block_start_date = datetime.utcfromtimestamp(start_date_unix / 1000).strftime('%Y-%m-%d')
                current_block_end_date = datetime.utcfromtimestamp(due_date_unix / 1000).strftime('%Y-%m-%d')

                crm_id = None
                current_am_id, current_developer_id = None, None
                for custom_field in blocking_data['custom_fields']:
                    if custom_field['id'] == "7084b6d7-c48a-4288-b779-35731156b2fa" and 'value' in custom_field:
                        dev_info_url = custom_field['value']
                        crm_id = dev_info_url.split("?")[0].replace("https://crm.zoho.com/crm/org55415226/tab/LinkingModule4/", "")
                    elif custom_field['id'] == "6400cee4-b94c-45a0-ac67-02ec18770c8e" and 'value' in custom_field:
                        current_am_id = custom_field['value'][0]['id'] if custom_field['value'] else None
                    elif custom_field['id'] == "912a953f-4c89-44cb-844d-603111aa7eb1" and 'value' in custom_field:
                        current_developer_id = custom_field['value'][0]['id'] if custom_field['value'] else None

                # GET DEV INFO DETAILS
                dev_info = None
                if crm_id:
                    dev_info = self.get_dev_info_details(crm_id)
                    if not dev_info:
                        print("requesting devionfo...")
                        dev_info = crm_get_records_by_id("Project_Details", crm_id)
                dev_info_status = dev_info['Status'] if dev_info else None

                # if dev_info_status == "OnHold":
                #     input("Dev info is on hold. skipping...")
                #     continue

                potential_id = dev_info['Multi_Select_Lookup_1']['id'] if dev_info and dev_info['Multi_Select_Lookup_1'] else None
                potential_details = self.get_potential(potential_id) if potential_id else None

                # GET CLICKUP MANAGER ID
                if not potential_id:
                    project_manager_email = ""
                elif potential_id == "1576533000386486133":
                    project_manager_email = "valia@kitrum.com"
                else:
                    potential_delivery = potential_details['Potential_Delivery_Owner']
                    project_manager_email = f'{potential_delivery.replace(" ", ".")}@kitrum.com'.lower() if potential_delivery else None
                clickup_manager_id = ""
                for clickup_user in self.clickup_users:
                    if project_manager_email == clickup_user['user']['email']:
                        clickup_manager_id = clickup_user['user']['id']
                    if clickup_manager_id:
                        break

                # CHECK IF FINAL DATE ON PROJECT IS THIS MONTH
                start_date_on_project = dev_info['Start_Date_on_Project'] if dev_info else None
                if start_date_on_project and str_to_date(start_date_on_project) > str_to_date(self.end_date):
                    input("KAKOITO PIZDEC TUT")
                final_date_on_project = dev_info['Final_Date_on_Project'] if dev_info else None

                finished_before_this_month = False
                if final_date_on_project and str_to_date(final_date_on_project) < str_to_date(self.start_date):
                    print("CHANGE BLOCKING HOURS TO 0")
                    print(f"FINISHED BEFORE MONTH START")
                    finished_before_this_month = True

                start_this_month = check_if_date_in_range(start_date_on_project, self.start_date, self.end_date)
                finish_this_month = check_if_date_in_range(final_date_on_project, self.start_date, self.end_date)

                # blocking_start_date = start_date_on_project if start_this_month else current_block_start_date
                # blocking_end_date = final_date_on_project if finish_this_month else current_block_end_date

                blocking_start_date = start_date_on_project if start_this_month else self.start_date
                blocking_end_date = final_date_on_project if finish_this_month else self.end_date

                # GET LEAVE HOURS WHICH ARE RELATED TO BLOCKING
                blocking_leave_hours = 0
                for leave_task_id in leave_task_ids:
                    leave_data = self.get_leave_details(leave_task_id)
                    if not leave_data:
                        leave_data = get_clickup_task_by_id(leave_task_id)
                    leave_start = datetime.utcfromtimestamp(int(leave_data['start_date']) / 1000).strftime('%Y-%m-%d')
                    leave_end = datetime.utcfromtimestamp(int(leave_data['due_date']) / 1000).strftime('%Y-%m-%d')
                    if str_to_date(leave_start) >= str_to_date(blocking_start_date) and str_to_date(leave_end) <= str_to_date(blocking_end_date):
                        for custom_field in leave_data['custom_fields']:
                            if custom_field['id'] == "5078d821-4695-4e09-ae6c-81e29081ef66":
                                blocking_leave_hours += round(float(custom_field['value']), 2)

                # CHECK WORKLOAD
                is_full_time_blocking = False
                for custom_field in blocking_data['custom_fields']:
                    if custom_field['id'] == "66c97dab-0d09-4dc2-9416-ae666a6e6d42":
                        if custom_field['value'] == 0:
                            is_full_time_blocking = True
                            break

                # BLOCKING MAIN FIELDS
                available = 0
                blocked = 0
                planned_leave = 0
                unplanned = 0
                current_leave = 0
                is_commercial = True
                for custom_field in blocking_data['custom_fields']:
                    # BLOCKED HOURS
                    if custom_field['id'] == "5078d821-4695-4e09-ae6c-81e29081ef66" and 'value' in custom_field:
                        blocked = round(float(custom_field['value']), 2)
                    # AVAILABLE HOURS
                    elif custom_field['id'] == "9a832c69-edab-40eb-a81d-03be6078b0d9" and 'value' in custom_field:
                        available = round(float(custom_field['value']), 2)
                    elif custom_field['id'] == "6d8b5aad-a01a-45ef-82a9-ae08698af25c" and 'value' in custom_field:
                        planned_leave = round(float(custom_field['value']), 2)
                        total_planned_leave_hours += round(float(custom_field['value']), 2)
                    elif custom_field['id'] == "7f3b4b79-b252-42ea-83fc-8c59445148f9" and 'value' in custom_field:
                        related_project_id = custom_field['value'][0]['id']
                        if related_project_id in internal_task_ids:
                            is_commercial = False
                    elif custom_field['id'] == "9ec43ad7-1d2a-404e-8a5e-fdfaa80e96bd" and 'value' in custom_field:
                        current_leave = round(float(custom_field['value']), 2)

                # NEW LOGIC
                unplanned = blocking_leave_hours - planned_leave if is_full_time_blocking and blocking_leave_hours > planned_leave else 0
                new_available = available
                new_blocked = blocked

                if finished_before_this_month:
                    new_blocked = 0
                    new_available = 0
                else:
                    if (start_this_month or finish_this_month) and is_full_time_blocking:
                        new_available = get_working_days(blocking_start_date, blocking_end_date) * hpd
                    if is_full_time_blocking:
                        if unplanned > 0:
                            new_blocked = new_available - planned_leave - unplanned
                            new_blocked = new_blocked if new_blocked > 0 else 0
                        else:
                            # old
                            # new_blocked = new_available - blocking_leave_hours if new_available > blocking_leave_hours else 0

                            # new
                            lts = planned_leave if planned_leave > blocking_leave_hours else blocking_leave_hours
                            new_blocked = new_available - lts if new_available > blocking_leave_hours else 0


                resource_total_blocked += new_blocked
                if is_commercial:
                    resource_commercial_hours += new_blocked
                else:
                    resource_internal_hours += new_blocked

                print(f"\t\tIs Full-time?: {is_full_time_blocking}")
                print(f"\t\tFinal Date on Project: {final_date_on_project}")
                print(f"\t\tAvailable Hours: {available}")
                print(f"\t\tBlocked Hours: {blocked}")
                print(f"\t\tFact Leave Hours: {leave_hours}")
                print(f"\t\tBlocking Leave Hours: {blocking_leave_hours}")
                print(f"\t\tPlanned Leave Hours: {planned_leave}")
                print(f"\t\tUnplanned Leave Hours: {unplanned}")
                print(f"\t\tNew Available: {new_available}")
                print(f"\t\tNew Blocked: {new_blocked}")
                print(f"\t\tAvailable change from {available} to {new_available}")
                print(f"\t\tBlocked change from {blocked} to {new_blocked}")
                print("\n")

                # BLOCKING CARD UPDATES
                # UPDATE FINAL DATE IF NEEDED
                if final_date_on_project:
                    update_dict = {}
                    if blocking_start_date != current_block_start_date:
                        # input(f"Updating Final Date to {blocking_start_date}")
                        update_dict["start_date"] = str_to_unix(blocking_start_date)
                    if blocking_end_date != current_block_end_date:
                        # input(f"Updating Final Date to {blocking_end_date}")
                        update_dict["due_date"] = str_to_unix(blocking_end_date)
                    if update_dict:
                        primary_block_update = clickup_update_task_data(blocking_task_id, update_dict)
                        print(f"PRIMARY TASK UPDATE: {primary_block_update['status']}")
                # UPDATE AM IF NEEDED
                if clickup_manager_id and clickup_manager_id != current_am_id:
                    # input(f"Updating AM from {current_am_id} to {clickup_manager_id}")
                    cf_am_update = clickup_update_cf(blocking_task_id, "6400cee4-b94c-45a0-ac67-02ec18770c8e", {"add": [clickup_manager_id], "rem": [current_am_id]})
                    print(f"AM UPDATE STATUS: {cf_am_update['status']}")
                # UPDATE DEV IF NEEDED
                if clickup_developer_id and clickup_developer_id != current_developer_id:
                    # input(f"Updating Developer from {current_developer_id} to {clickup_developer_id}")
                    cf_dev_update = clickup_update_cf(blocking_task_id, "912a953f-4c89-44cb-844d-603111aa7eb1", {"add": [clickup_developer_id], "rem": [current_developer_id]})
                    print(f"DEV UPDATE STATUS: {cf_dev_update['status']}")
                # UPDATE BLOCKED HOURS IF NEEDED
                if blocked != new_blocked:
                    # input(f"Updating Blocked Hours from {blocked} to {new_blocked}")
                    cf_blocked_update = clickup_update_cf(blocking_task_id, "5078d821-4695-4e09-ae6c-81e29081ef66", str(new_blocked))
                    print(f"BLOCKED HOURS UPDATE STATUS: {cf_blocked_update['status']}")
                # UPDATE AVAILABLE HOURS IF NEEDED
                if available != new_available:
                    # input(f"Updating Available Hours from {available} to {new_available}")
                    cf_available_update = clickup_update_cf(blocking_task_id, "9a832c69-edab-40eb-a81d-03be6078b0d9", str(new_available))
                    print(f"AVAILABLE HOURS UPDATE STATUS: {cf_available_update['status']}")
                if is_full_time_blocking and blocking_leave_hours > 0 and blocking_leave_hours != current_leave:
                    # input(f"Updating Leave Hours from {current_leave} to {blocking_leave_hours}")
                    cf_leave_update = clickup_update_cf(blocking_task_id, "9ec43ad7-1d2a-404e-8a5e-fdfaa80e96bd", blocking_leave_hours)
                    print(f"LEAVE HOURS UPDATE STATUS: {cf_leave_update['status']}")

            if exited_before_this_month:
                resource_free_hours = 0
            else:
                # old
                # resource_free_hours = new_resource_total_available - resource_total_blocked - leave_hours
                rlts = total_planned_leave_hours if total_planned_leave_hours > leave_hours else leave_hours
                resource_free_hours = new_resource_total_available - resource_total_blocked - rlts

            print(f"Resource Available: {new_resource_total_available}")
            print(f"Resource Total Blocked: {resource_total_blocked}")
            print(f"Resource Commercial Hours: {resource_commercial_hours}")
            print(f"Resource Internal Hours: {resource_internal_hours}")
            print(f"Resource Free Hours: {resource_free_hours}")

            try:
                if new_resource_total_available > 0:
                    # old
                    # utilization_percent = round(resource_commercial_hours / (new_resource_total_available - resource_internal_hours - leave_hours) * 100, 2)
                    rlts = total_planned_leave_hours if total_planned_leave_hours > leave_hours else leave_hours
                    utilization_percent = round(resource_commercial_hours / (new_resource_total_available - resource_internal_hours - rlts) * 100, 2)

                else:
                    utilization_percent = 0
            except:
                utilization_percent = 0
            print(f"Resource Unitization Percent: {utilization_percent}")

            # UPDATE FREE HOURS IF NEEDED
            if exited_before_this_month:
                resource_update_dict = {"start_date": str_to_unix(self.start_date), "due_date": str_to_unix(self.end_date)}
                primary_resource_update = clickup_update_task_data(resource_id, resource_update_dict)
                print(f"PRIMARY TASK UPDATE: {primary_resource_update['status']}")
            if new_resource_total_available != resource_total_available:
                resource_update_dict = {"start_date": str_to_unix(resource_start_date), "due_date": str_to_unix(resource_end_date)}
                primary_resource_update = clickup_update_task_data(resource_id, resource_update_dict)
                print(f"PRIMARY TASK UPDATE: {primary_resource_update['status']}")
                cf_monthly_hours_update = clickup_update_cf(resource_id, "3fac0ff8-6981-463a-b7e0-a375f86aed24", str(new_resource_total_available))
                print(f"RESOURCE MONTHLY HOURS UPDATE STATUS: {cf_monthly_hours_update['status']}")
            if current_free_hours != resource_free_hours or resource_free_hours == 0:
                # input(f"Updating Free Hours from {current_free_hours} to {resource_free_hours}")
                cf_free_hours_update = clickup_update_cf(resource_id, "cf0b9445-8383-4d93-bc56-52a2c2c551b7", str(resource_free_hours))
                print(f"FREE HOURS UPDATE STATUS: {cf_free_hours_update['status']}")
            # UPDATE UTILIZATION IF NEEDED
            if current_utilization != utilization_percent or utilization_percent == 0:
                # input(f"Updating Utilization from {current_utilization} to {utilization_percent}")
                cf_utilization_update = clickup_update_cf(resource_id, "703dd683-1188-4427-a1a3-205733badd3f", str(utilization_percent))
                print(f"UTILIZATION UPDATE STATUS: {cf_utilization_update['status']}")
            # UPDATE DEV IF NEEDED
            if clickup_developer_id and clickup_developer_id != resource_current_developer_id:
                # input(f"Updating Developer from {resource_current_developer_id} to {clickup_developer_id}")
                cf_dev_update = clickup_update_cf(resource_id, "912a953f-4c89-44cb-844d-603111aa7eb1", {"add": [clickup_developer_id], "rem": [resource_current_developer_id]})
                print(f"DEV UPDATE STATUS: {cf_dev_update['status']}")


def resource_calculator(month_start_date, month_end_date):
    resource_calculation = ResourceCalculation(month_start_date, month_end_date)
    resource_calculation.launch()


# date_ranges = [{"start": '2025-04-01', "end": '2025-04-30'}, {"start": '2025-05-01', "end": '2025-05-31'}, {"start": '2025-06-01', "end": '2025-06-30'}]
# date_ranges = [{"start": '2025-07-01', "end": '2025-07-31'}, {"start": '2025-08-01', "end": '2025-08-31'}, {"start": '2025-09-01', "end": '2025-09-30'}]
# date_ranges = [{"start": '2025-09-01', "end": '2025-09-30'}]


def launch_calculator():
    for date_range in date_ranges:
        print("-----" * 10)
        print(f"Current Date Range: {date_range}")
        resource_calculator(date_range['start'], date_range['end'])




