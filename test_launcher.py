from scripts.resource_calculator import launch_calculator
from scripts.resource_creator import launch_creator
from scripts.available_resources import available_resources_collector
from scripts.timelogs_crosschecker import cross_check_sync_launcher
from scripts.clickup_timelogs_sync import timelog_sync_launcher
from datetime import datetime
from scripts.zp_timesheet_creator import launch_timesheets_submit

# timelog_sync_launcher('2025-06-01', '2025-06-30', ["artem.iakovenko@kitrum.com"])

# users = [
#     'yuliia.pabot@kitrum.com',
# ]


# cross_check_sync_launcher('2025-07-01', '2025-07-31')
# timelog_sync_launcher('2025-07-01', '2025-07-31', ["yevgen.sboychakov@kitrum.com"])
# launch_timesheets_submit('2025-07-01', '2025-07-31', users)
available_resources_collector()
# launch_calculator()
