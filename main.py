import json
from typing import Tuple
import requests
import time


def load_credentials():
    with open('credentials.json', 'r') as f:
        return json.load(f)


def power_status(credentials):
    auth = {'Authorization': 'Bearer ' + credentials['access_token']}
    r = requests.get(
        'https://owner-api.teslamotors.com/api/1/energy_sites/194082077326/live_status', headers=auth)
    return r.json()['response']


def vehicle_status(credentials):
    auth = {'Authorization': 'Bearer ' + credentials['access_token']}
    r = requests.get(
        'https://owner-api.teslamotors.com/api/1/vehicles/1492931321740893/data_request/charge_state', headers=auth)
    return r.json()['response']


def set_charging_amp(credentials, status, amp):
    auth = {'Authorization': 'Bearer ' + credentials['access_token']}
    if amp == 0:
        print("Stopping charging")
        r = requests.post(
            'https://owner-api.teslamotors.com/api/1/vehicles/1492931321740893/command/charge_stop', headers=auth)
        print(r.json())
        return

    if status['charging_state'] == 'Stopped' and amp > 1:
        print("Starting charging")
        r = requests.post(
            'https://owner-api.teslamotors.com/api/1/vehicles/1492931321740893/command/charge_start', headers=auth)
        print(r.json())
    print("Setting Charging Amp: {}".format(amp))
    r = requests.post('https://owner-api.teslamotors.com/api/1/vehicles/1492931321740893/command/set_charging_amps',
                      headers=auth, json={'charging_amps': amp})
    print(r.json())


def get_charging_power(vehicle) -> Tuple[int, int, int]:
    if vehicle['charging_state'] == 'Stopped':
        print("Charging is stopped")
        return 240, 0, 0
    else:
        amp = vehicle['charger_actual_current']
        voltage = vehicle['charger_voltage']
        power = amp * voltage
        print("Current charging {}V * {}A = {}W".format(voltage, amp, power))
        return voltage, amp, power


def main():
    credentials = load_credentials()

    while True:
        power = power_status(credentials)
        vehicle = vehicle_status(credentials)
        if vehicle is None or 'charger_actual_current' not in vehicle:
            print('Cannot get vehicle status')
            time.sleep(30)
            continue

        voltage, current_charging_amp, charging_power = get_charging_power(
            vehicle)
        surplus = power['solar_power'] - power['load_power'] + charging_power
        charging_amp = round(max(0, min(40, surplus / voltage)))

        print("Solar: {}W, Load (House): {}W".format(
            power['solar_power'], power['load_power'] - charging_power))
        print("Surplus: {}W, Load (Vehicle): {}W, Battery: {}W, Grid: {}W".format(
            surplus, charging_power, power['battery_power'], power['grid_power']))

        if charging_amp != current_charging_amp:
            set_charging_amp(credentials, vehicle, charging_amp)

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
