import json
import requests
from zoho_api.auth import ZohoAuth
success_status_codes = [200, 201, 400]


zoho_people_auth = ZohoAuth("zoho_people")
zoho_books_auth = ZohoAuth("zoho_books")
zoho_creator_auth = ZohoAuth("zoho_creator")
zoho_crm_auth = ZohoAuth("zoho_crm")

def api_request(url, source, method, post_data):
    access_headers = {}
    if source == 'zoho_people':
        zoho_people_auth.get_or_refresh_access_token()
        access_headers = {
            'Authorization': f'Zoho-oauthtoken {zoho_people_auth.access_token}'
        }
    elif source == 'zoho_books':
        zoho_books_auth.get_or_refresh_access_token()
        access_headers = {
            'Authorization': f'Zoho-oauthtoken {zoho_books_auth.access_token}'
        }
    elif source == 'zoho_creator':
        zoho_creator_auth.get_or_refresh_access_token()
        access_headers = {
            'Authorization': f'Zoho-oauthtoken {zoho_creator_auth.access_token}'
        }
    elif source == 'zoho_crm':
        zoho_crm_auth.get_or_refresh_access_token()
        access_headers = {
            'Authorization': f'Zoho-oauthtoken {zoho_crm_auth.access_token}'
        }

    if access_headers:
        if method == 'get':
            response = requests.get(url, headers=access_headers)
        elif method == 'put':
            response = requests.put(url, headers=access_headers, data=json.dumps(post_data))
        elif method == 'post':
            response = requests.post(url, headers=access_headers, data=json.dumps(post_data))
        elif method == 'patch':
            response = requests.patch(url, headers=access_headers, data=json.dumps(post_data))
        if response.status_code in success_status_codes:
            return response.json()
        else:
            return None
    else:
        return None
