import time
import requests
import json


class TeslaAuth(requests.auth.AuthBase):
    def __init__(self, file) -> None:
        self.file = file
        with open(file, 'r') as f:
            self.token = json.load(f)

    def __call__(self, r):
        if self.token['issued_at'] + self.token['expires_in'] < time.time():
            self.refresh_token()
        r.headers['Authorization'] = 'Bearer ' + self.token['access_token']
        return r

    def refresh_token(self):
        url = 'https://auth.tesla.com/oauth2/v3/token'
        payload = {
            'client_id': 'ownerapi',
            'scope': 'openid email offline_access',
            'grant_type': 'refresh_token',
            'refresh_token': self.token['refresh_token']
        }
        r = requests.post(url, json=payload)
        r.raise_for_status()
        self.token = r.json()
        self.token['issued_at'] = time.time()
        with open(self.file, 'w') as f:
            json.dump(self.token, f)


class TeslaAPI:
    def __init__(self, auth):
        self.auth = auth

    def power_status(self, site_id):
        return requests.get(
            f'https://owner-api.teslamotors.com/api/1/energy_sites/{site_id}/live_status',
            auth=self.auth)

    def vehicle_status(self, vehicle_id):
        return requests.get(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/data_request/charge_state',
            auth=self.auth)

    def charge_stop(self, vehicle_id):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_stop',
            auth=self.auth)

    def charge_start(self, vehicle_id):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_start',
            auth=self.auth)

    def set_charging_amp(self, vehicle_id, amp):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/set_charging_amps',
            auth=self.auth,
            json={'charging_amps': amp})
