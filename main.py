import json
import time
import api

from typing import Tuple


def create_api() -> api.Tesla:
    with open('credentials.json', 'r') as f:
        return api.Tesla(json.load(f))


def load_ids():
    with open('id.json', 'r') as f:
        return json.load(f)


def set_charging_amp(tesla, vehicle_id, status, amp):
    if amp == 0:
        print("Stopping charging")
        r = tesla.charge_stop(vehicle_id)
        print(r.json())
        return

    if status['charging_state'] == 'Stopped' and amp > 1:
        print("Starting charging")
        r = tesla.charge_start(vehicle_id)
        print(r.json())
    print("Setting Charging Amp: {}".format(amp))
    r = tesla.set_charging_amp(vehicle_id, amp)
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
    tesla = create_api()
    ids = load_ids()

    site_id = ids['energy']
    vehicle_id = ids['vehicle']

    while True:
        power = tesla.power_status(site_id).json()['response']
        vehicle = tesla.vehicle_status(vehicle_id).json()['response']
        if vehicle is None or 'charger_actual_current' not in vehicle:
            print('Cannot get vehicle status')
            time.sleep(30)
            continue
        if vehicle['charging_state'] == 'Disconnected':
            print('Charger is disconnected')
            break

        voltage, current_charging_amp, charging_power = get_charging_power(
            vehicle)
        surplus = power['solar_power'] - power['load_power'] + charging_power
        charging_amp = round(max(0, min(40, surplus / voltage)))

        print("Solar: {}W, Load (House): {}W".format(
            power['solar_power'], power['load_power'] - charging_power))
        print("Surplus: {}W, Load (Vehicle): {}W, Battery: {}W, Grid: {}W".format(
            surplus, charging_power, power['battery_power'], power['grid_power']))

        if charging_amp != current_charging_amp:
            set_charging_amp(tesla, vehicle, charging_amp)

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
