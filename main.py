import json
import time
import api

from typing import Tuple


def load_ids():
    with open('id.json', 'r') as f:
        return json.load(f)


class Vehicle:
    def __init__(self, api, vehicle_id) -> None:
        self.api = api
        self.vehicle_id = vehicle_id
        self.refresh_status()

    def refresh_status(self):
        self.status = self.api.vehicle_status(
            self.vehicle_id).json()['response']
        return self.status

    def set_charging_amp(self, amp):
        if amp == 0:
            print("Stopping charging")
            r = self.api.charge_stop(self.vehicle_id)
            print(r.json())
            return

        if self.status['charging_state'] == 'Stopped' and amp > 1:
            print("Starting charging")
            r = self.api.charge_start(self.vehicle_id)
            print(r.json())
        print("Setting Charging Amp: {}".format(amp))
        r = self.api.set_charging_amp(self.vehicle_id, amp)
        print(r.json())

    def get_charging_power(self) -> Tuple[int, int, int]:
        if self.status['charging_state'] == 'Stopped':
            print("Charging is stopped")
            return 240, 0, 0
        else:
            amp = self.status['charger_actual_current']
            voltage = self.status['charger_voltage']
            power = amp * voltage
            print("Current charging {}V * {}A = {}W".format(voltage, amp, power))
            return voltage, amp, power


def get_powerwall_power(powerwall) -> int:
    percent = powerwall['percentage_charged']
    if percent < 89:
        print("Powerwall is {:.2f}% charged, allowing 5kW".format(percent))
        return 5000
    if percent > 91:
        print("Powerwall is {:.2f}% charged, allowing -5kW".format(percent))
        return -5000
    print("Powerwall is {:.2f}% charged, holding".format(percent))
    return 0


def main():
    tesla = api.TeslaAPI(api.TeslaAuth('credentials.json'))
    ids = load_ids()

    site_id = ids['energy']
    vehicle_id = ids['vehicle']
    vehicle = Vehicle(tesla, vehicle_id)

    while True:
        power = tesla.power_status(site_id).json()['response']
        status = vehicle.refresh_status()
        if status is None or 'charger_actual_current' not in status:
            print('Cannot get vehicle status')
            time.sleep(30)
            continue
        if status['charging_state'] == 'Disconnected':
            print('Charger is disconnected')
            break

        voltage, current_charging_amp, charging_power = vehicle.get_charging_power()
        powerwall_power = get_powerwall_power(power)
        surplus = power['solar_power'] - power['load_power'] + charging_power

        print("Solar: {}W, Load (House): {}W".format(
            power['solar_power'], power['load_power'] - charging_power))
        print("Surplus: {}W, Load (Vehicle): {}W, Battery: {}W, Grid: {}W".format(
            surplus, charging_power, power['battery_power'], power['grid_power']))

        charging_amp = round(max(0, min(40, surplus / voltage)))
        if charging_amp != current_charging_amp:
            vehicle.set_charging_amp(charging_amp)

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
