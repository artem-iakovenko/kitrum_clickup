from scripts.resource_calculator import launch_calculator
from scripts.resource_creator import launch_creator
from scripts.available_resources import available_resources_collector
from scripts.timelogs_crosschecker import cross_check_sync_launcher
from datetime import datetime
# timelog_sync_launcher('2025-06-01', '2025-06-30', ["artem.iakovenko@kitrum.com"])


# cross_check_sync_launcher('2025-06-01', '2025-06-30')
# timelog_sync_launcher('2025-06-01', '2025-06-30', ['kateryna.lytvynova@kitrum.com'])
available_resources_collector()
