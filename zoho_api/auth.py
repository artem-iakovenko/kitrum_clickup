import requests
import datetime
from datetime import timedelta
import json
from secret_manager import access_secret


class ZohoAuth:
    def __init__(self, source):
        self.source = source
        self.client_id = None
        self.client_secret = None
        self.refresh_token = None
        self.access_token = None
        self.expiration_date = None

    def get_or_refresh_access_token(self):
        if self.check_expiration():
            oauth_creds = json.loads(access_secret("kitrum-cloud", self.source))
            self.client_id = oauth_creds['client_id']
            self.client_secret = oauth_creds['client_secret']
            self.refresh_token = oauth_creds['refresh_token']
            access_token_response = requests.post(
                f'https://accounts.zoho.com/oauth/v2/token?refresh_token={self.refresh_token}&client_id={self.client_id}&client_secret={self.client_secret}&grant_type=refresh_token')
            if access_token_response.status_code == 200:
                response_json = access_token_response.json()
                self.access_token = response_json['access_token']
                current_time = datetime.datetime.now()
                expiry_date = current_time + timedelta(minutes=55)
                self.expiration_date = expiry_date
            else:
                print('Error While Refreshing a Token')

    def check_expiration(self):
        expiration_date = self.expiration_date
        access_token = self.access_token
        if not expiration_date or not access_token:
            return True
        current_time = datetime.datetime.now()
        return True if current_time >= expiration_date else False
