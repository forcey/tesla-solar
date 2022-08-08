import datetime
import time
import api
import os

from zoneinfo import ZoneInfo
from typing import Tuple


class Vehicle:
    def __init__(self, api, vehicle_id, display_name) -> None:
        self.api = api
        self.vehicle_id = vehicle_id
        self.display_name = display_name

    def refresh_status(self):
        config = self.api.vehicle_config(self.vehicle_id)
        if config.get('state') == 'asleep':
            return 'asleep'
        else:
            self.charge_state = self.api.charge_state(self.vehicle_id)
            return self.charge_state.get('charging_state')

    def wake_up(self):
        r = self.api.wake_up(self.vehicle_id)
        print(r.response())

    def _set_charging_amp(self, amp):
        if amp == 0:
            print("Stopping charging")
            r = self.api.charge_stop(self.vehicle_id)
            print(r.response())
            return

        if self.charge_state.get('charging_state') == 'Stopped':
            print("Starting charging")
            r = self.api.charge_start(self.vehicle_id)
            print(r.response())
        print("Setting Charging Amp: {}".format(amp))
        r = self.api.set_charging_amp(self.vehicle_id, amp)
        print(r.response())

    def get_charging_power(self) -> Tuple[int, int, int]:
        if self.charge_state.get('charging_state') == 'Stopped':
            print("Charging is stopped")
            return 240, 0, 0
        else:
            amp = self.charge_state.get('charger_actual_current')
            voltage = self.charge_state.get('charger_voltage')
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
        self._solar_counter = StatCounter(cap=900)

    def refresh_status(self):
        self.status = self.api.power_status(self.site_id)
        self._solar_counter.add(self.status.get('solar_power'))
        return self.status

    def percent_charged(self):
        return self.status.get('percentage_charged')

    def has_enough_power(self) -> bool:
        if self._solar_counter.get_average() > 1000:
            return True
        else:
            print("Average solar input in the last {} readings is {}W".format(
                self._solar_counter.length(), self._solar_counter.get_average()))
            return False

    def allocate_power(self) -> int:
        percent = self.percent_charged()
        if percent < 90:
            # Watts required to charge to 90% in 5 minutes.
            watts = min(5000, (90-percent) *
                        self.status.get('total_pack_energy') / 100 * 60 / 5)
            print(
                "Powerwall is {:.2f}% charged, allowing {}W to powerwall.".format(percent, round(watts)))
            return watts
        print("Powerwall is {:.2f}% charged, holding".format(percent))
        return 0


class StatCounter:
    # Cap in seconds
    def __init__(self, cap) -> None:
        self.cap = cap
        # Elements are (timestamp, value)
        self.values = []
        self.sum = 0

    def add(self, value):
        self.values.append((time.time(), value))
        self.sum += value
        self.remove_old()

    def remove_old(self):
        cutoff = time.time() - self.cap
        for i in range(len(self.values)):
            if self.values[i][0] < cutoff:
                self.sum -= self.values[i][1]
            else:
                break
        self.values = self.values[i:]

    def length(self) -> int:
        return len(self.values)

    def get_average(self):
        return float(self.sum) / len(self.values)


def is_daytime():
    now = datetime.datetime.now(tz=ZoneInfo("America/Los_Angeles"))
    return now.hour >= 9 and now.hour < 18


class Session:
    def __init__(self, vehicle, powerwall) -> None:
        self._vehicle = vehicle
        self._powerwall = powerwall
        self._surplus_counter = StatCounter(cap=300)
        pass

    def start(self):
        print("Starting session with vehicle {} and powerwall {}".format(
            self._vehicle.display_name, self._powerwall.display_name))

        error_count = 0
        while True:
            try:
                if self._cycle():
                    error_count = 0
                else:
                    break
            except api.APIError as e:
                error_count += 1
                print("Error #{}: {}".format(error_count, e))
                if error_count >= 3:
                    print("Too many errors, ending session")
                    break
            print('\n')
            time.sleep(30)

    # Returns True if the loop should continue, False if it should end.
    def _cycle(self) -> bool:
        print(datetime.datetime.now())
        power = self._powerwall.refresh_status()
        status = self._vehicle.refresh_status()
        if not (is_daytime() and self._powerwall.has_enough_power()):
            print("Outside of day time and not enough power, ending session.")
            return False
        if status == 'asleep':
            print('Vehicle is asleep, waking up')
            self._vehicle.wake_up()
            return True
        if status == 'Disconnected':
            print('Charger is disconnected, session completed.')
            return False
        if status == 'Complete':
            print('Charging is completed, session completed.')
            return False

        voltage, _, current_charging_power = self._vehicle.get_charging_power()

        surplus = power.get('solar_power') - \
            power.get('load_power') + current_charging_power

        print("Solar: {}W -> House: {}W".format(
            round(power.get('solar_power')), round(power.get('load_power') - current_charging_power)))
        print("Surplus: {}W -> Vehicle: {}W, Powerwall: {}W, Grid: {}W".format(
            round(surplus), round(-current_charging_power), round(power.get('battery_power')), round(power.get('grid_power'))))

        self._surplus_counter.add(surplus)
        average_surplus = self._surplus_counter.get_average()
        print("Average surplus of the last {} readings: {}W".format(
            self._surplus_counter.length(), round(average_surplus)))

        powerwall_power = self._powerwall.allocate_power()
        next_charging_power = max(0, average_surplus - powerwall_power)
        if abs(next_charging_power - current_charging_power) > 250 or \
                (current_charging_power > 0 and next_charging_power == 0):
            print("Charging power is {}W, setting to {}W".format(
                round(current_charging_power), round(next_charging_power)))
            self._vehicle.set_charging_power(next_charging_power, voltage)
        return True


def main():
    path = os.environ.get('CREDENTIALS', 'credentials.json')
    tesla = api.TeslaAPI(api.TeslaAuth(path))

    # Find available products
    vehicles = []
    powerwalls = []
    products = tesla.product_list()
    for product in products.response():
        if 'vin' in product:
            print("Found vehicle: {}".format(product['display_name']))
            vehicles.append(
                Vehicle(tesla, product['id'], product['display_name']))
        elif 'energy_site_id' in product:
            print("Found powerwall: {}".format(product['site_name']))
            powerwalls.append(
                Powerwall(tesla, product['energy_site_id'], product['site_name']))

    powerwall = powerwalls[0]
    while True:
        powerwall.refresh_status()
        if not (is_daytime() and powerwall.has_enough_power()):
            print("Outside of day time and not enough power, sleeping for an hour.")
            time.sleep(3600)

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

            session = Session(vehicle, powerwall)
            session.start()

        print('\n')
        time.sleep(300)


if __name__ == '__main__':
    main()
