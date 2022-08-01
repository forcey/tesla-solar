import time
import api

from typing import Tuple


class Vehicle:
    def __init__(self, api, vehicle_id, display_name) -> None:
        self.api = api
        self.vehicle_id = vehicle_id
        self.display_name = display_name

    def refresh_status(self):
        config = self.api.vehicle_config(self.vehicle_id).json()['response']
        if config['state'] == 'asleep':
            return 'asleep'
        else:
            json = self.api.charge_state(self.vehicle_id).json()
            self.charge_state_json = json['response']
            if self.charge_state_json is None:
                print("Cannot get charge state for {}, response: {}".format(
                    self.display_name, json))
            if 'charger_actual_current' not in self.charge_state_json:
                print("Cannot get charger_actual_current for {}, response: {}".format(
                    self.display_name, json))
            return self.charge_state_json['charging_state']

    def wake_up(self):
        r = self.api.wake_up(self.vehicle_id)
        print(r.json())

    def _set_charging_amp(self, amp):
        if amp == 0:
            print("Stopping charging")
            r = self.api.charge_stop(self.vehicle_id)
            print(r.json())
            return

        if self.charge_state_json['charging_state'] == 'Stopped':
            print("Starting charging")
            r = self.api.charge_start(self.vehicle_id)
            print(r.json())
        print("Setting Charging Amp: {}".format(amp))
        r = self.api.set_charging_amp(self.vehicle_id, amp)
        print(r.json())

    def get_charging_power(self) -> Tuple[int, int, int]:
        if self.charge_state_json['charging_state'] == 'Stopped':
            print("Charging is stopped")
            return 240, 0, 0
        else:
            amp = self.charge_state_json['charger_actual_current']
            voltage = self.charge_state_json['charger_voltage']
            power = amp * voltage
            print("Current charging {}V * {}A = {}W".format(voltage, amp, power))
            return voltage, amp, power

    def set_charging_power(self, power, voltage):
        amp = round(max(0, min(40, power / voltage)))
        self._set_charging_amp(amp)


class Powerwall:
    def __init__(self, api, site_id, display_name):
        self.api = api
        self.site_id = site_id
        self.display_name = display_name

    def refresh_status(self):
        self.status = self.api.power_status(self.site_id).json()['response']
        return self.status

    def allocate_power(self) -> int:
        percent = self.status['percentage_charged']
        if percent < 90:
            # Watts required to charge to 90% in 5 minutes.
            watts = min(5000, (90-percent) *
                        self.status['total_pack_energy'] / 100 * 60 / 5)
            print(
                "Powerwall is {:.2f}% charged, allowing {}W to powerwall.".format(percent, round(watts)))
            return watts
        print("Powerwall is {:.2f}% charged, holding".format(percent))
        return 0


def start_session(vehicle, powerwall):
    print("Starting session with vehicle {} and powerwall {}".format(
        vehicle.display_name, powerwall.display_name))
    while True:
        power = powerwall.refresh_status()
        status = vehicle.refresh_status()
        if status == 'asleep':
            print('Vehicle is asleep, waking up')
            vehicle.wake_up()
            print('\n')
            time.sleep(30)
            continue
        if status == 'Disconnected':
            print('Charger is disconnected, session completed.')
            return
        if status == 'Complete':
            print('Charging is completed, session completed.')
            return

        voltage, _, current_charging_power = vehicle.get_charging_power()
        surplus = power['solar_power'] - \
            power['load_power'] + current_charging_power

        print("Solar: {}W -> House: {}W".format(
            round(power['solar_power']), round(power['load_power'] - current_charging_power)))
        print("Surplus: {}W -> Vehicle: {}W, Powerwall: {}W, Grid: {}W".format(
            round(surplus), round(-current_charging_power), round(power['battery_power']), round(power['grid_power'])))

        powerwall_power = powerwall.allocate_power()
        next_charging_power = max(0, surplus - powerwall_power)
        if abs(next_charging_power - current_charging_power) > 500 or next_charging_power == 0:
            print("Charging power is {}W, setting to {}W".format(
                round(current_charging_power), round(next_charging_power)))
            vehicle.set_charging_power(next_charging_power, voltage)

        print('\n')
        time.sleep(30)


def main():
    tesla = api.TeslaAPI(api.TeslaAuth('credentials.json'))

    # Find available products
    vehicles = []
    powerwalls = []
    products = tesla.product_list().json()['response']
    for product in products:
        if 'vin' in product:
            print("Found vehicle: {}".format(product['display_name']))
            vehicles.append(
                Vehicle(tesla, product['id'], product['display_name']))
        elif 'energy_site_id' in product:
            print("Found powerwall: {}".format(product['site_name']))
            powerwalls.append(
                Powerwall(tesla, product['energy_site_id'], product['site_name']))

    while True:
        for vehicle in vehicles:
            status = vehicle.refresh_status()
            if status == 'asleep':
                print("Vehicle {} is asleep".format(vehicle.display_name))
                continue
            if status == 'Disconnected':
                print("Vehicle {} is disconnected".format(vehicle.display_name))
                continue
            if status == 'Complete':
                print("Vehicle {} is completed".format(vehicle.display_name))
                continue

            start_session(vehicle, powerwalls[0])

        print('\n')
        time.sleep(30)


if __name__ == '__main__':
    main()
