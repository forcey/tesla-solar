import json
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


def set_charging_amp(credentials, amp):
    auth = {'Authorization': 'Bearer ' + credentials['access_token']}
    r = requests.post('https://owner-api.teslamotors.com/api/1/vehicles/1492931321740893/command/set_charging_amps',
                      headers=auth, json={'charging_amps': amp})
    print(r.json())


def main():
    credentials = load_credentials()

    while True:
        power = power_status(credentials)
        vehicle = vehicle_status(credentials)
        if 'charger_actual_current' not in vehicle:
            print('Cannot get vehicle status')
            time.sleep(30)
            continue
        
        current_charging_amp = vehicle['charger_actual_current']
        voltage = vehicle['charger_voltage']
        charging_power = current_charging_amp * voltage

        surplus = power['solar_power'] - power['load_power'] + charging_power
        charging_amp = round(max(0, min(40, surplus / 240)))

        print("Current charging {}V * {}A = {}W".format(voltage,
              current_charging_amp, charging_power))
        print("Solar: {}W, Load (House): {}W".format(
            power['solar_power'], power['load_power'] - charging_power))
        print("Surplus: {}W, Load (Vehicle): {}W, Battery: {}W, Grid: {}W".format(
            surplus, charging_power, power['battery_power'], power['grid_power']))

        if charging_amp != current_charging_amp:
            print("Setting Charging Amp: {}".format(charging_amp))
            set_charging_amp(credentials, charging_amp)

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
