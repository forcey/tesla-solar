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

    def _set_charging_amp(self, amp):
        if amp == 0:
            print("Stopping charging")
            r = self.api.charge_stop(self.vehicle_id)
            print(r.json())
            return

        if self.status['charging_state'] == 'Stopped':
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

    def set_charging_power(self, power, voltage):
        amp = round(max(0, min(40, power / voltage)))
        self._set_charging_amp(amp)


def get_powerwall_power(powerwall) -> int:
    percent = powerwall['percentage_charged']
    if percent < 90:
        # Watts required to charge to 90% in 5 minutes.
        watts = min(5000, (90-percent) *
                    powerwall['total_pack_energy'] / 100 * 60 / 5)
        print(
            "Powerwall is {:.2f}% charged, allowing {}W to powerwall.".format(percent, round(watts)))
        return watts
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

        voltage, _, current_charging_power = vehicle.get_charging_power()
        powerwall_power = get_powerwall_power(power)
        surplus = power['solar_power'] - \
            power['load_power'] + current_charging_power

        print("Solar: {}W -> House: {}W".format(
            round(power['solar_power']), round(power['load_power'] - current_charging_power)))
        print("Surplus: {}W -> Vehicle: {}W, Powerwall: {}W, Grid: {}W".format(
            round(surplus), round(-current_charging_power), round(power['battery_power']), round(power['grid_power'])))

        next_charging_power = max(0, surplus - powerwall_power)
        if abs(next_charging_power - current_charging_power) > 500 or next_charging_power == 0:
            print("Charging power is {}W, setting to {}W".format(
                round(current_charging_power), round(next_charging_power)))
            vehicle.set_charging_power(next_charging_power, voltage)

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
