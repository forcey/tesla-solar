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
            json.dump(self.token, f, indent=2)


class APIError(Exception):
    pass


class TeslaAPI:
    def __init__(self, auth):
        self.session = requests.Session()
        self.session.auth = auth
        self.session.mount(
            'https://', requests.adapters.HTTPAdapter(max_retries=3))

    # Product list API
    def product_list(self):
        return self.session.get('https://owner-api.teslamotors.com/api/1/products')

    # Vehicle API
    def vehicle_config(self, vehicle_id):
        return self.session.get(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}')

    def wake_up(self, vehicle_id):
        return self.session.post(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/wake_up')

    def charge_state(self, vehicle_id):
        return self.session.get(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/data_request/charge_state')

    def charge_stop(self, vehicle_id):
        return self.session.post(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_stop')

    def charge_start(self, vehicle_id):
        return self.session.post(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_start')

    def set_charging_amp(self, vehicle_id, amp):
        return self.session.post(f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/set_charging_amps',
                                 json={'charging_amps': amp})

    # Powerwall API
    def power_status(self, site_id):
        return self.session.get(f'https://owner-api.teslamotors.com/api/1/energy_sites/{site_id}/live_status')

    # JSON API
    def get_response(self, r: requests.Response):
        try:
            js = r.json()
        except requests.exceptions.JSONDecodeError:
            raise APIError(f'Cannot decode JSON: {r.text}')
        if js['response'] is not None:
            return js['response']
        else:
            raise APIError(f'No response: {js["error"]}')
