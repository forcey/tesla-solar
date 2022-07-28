import requests


class Tesla:
    def __init__(self, credentials):
        self.credentials = credentials

    def _auth_header(self):
        return {'Authorization': 'Bearer ' + self.credentials['access_token']}

    def power_status(self, site_id):
        return requests.get(
            f'https://owner-api.teslamotors.com/api/1/energy_sites/{site_id}/live_status',
            headers=self._auth_header())

    def vehicle_status(self, vehicle_id):
        return requests.get(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/data_request/charge_state',
            headers=self._auth_header())

    def charge_stop(self, vehicle_id):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_stop',
            headers=self._auth_header())

    def charge_start(self, vehicle_id):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/charge_start',
            headers=self._auth_header())

    def set_charging_amp(self, vehicle_id, amp):
        return requests.post(
            f'https://owner-api.teslamotors.com/api/1/vehicles/{vehicle_id}/command/set_charging_amps',
            headers=self._auth_header(),
            json={'charging_amps': amp})
