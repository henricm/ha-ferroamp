"""Ferroamp EnergyHub, SSO and ESO sensors"""

import uuid
import json
import logging

from homeassistant.core import callback
from homeassistant.components import mqtt

CONTROL_REQUEST = "extapi/control/request"
ATTR_POWER = "power"
DEFAULT_POWER = 1000

_LOGGER = logging.getLogger(__name__)

def setup(hass, config):

    _LOGGER.debug("Setting up ferroamp battery service calls")

    def control_request(cmd_name, power = None):
        cmd = { "name": cmd_name }
        if power is not None:
            cmd["arg"] = power

        payload = {
            "transId": str(uuid.uuid1()),
            "cmd": cmd
        }

        _LOGGER.debug(f"Sending control request {cmd} with payload {payload}")

        mqtt.async_publish(hass, CONTROL_REQUEST, json.dumps(payload))


    def charge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        _LOGGER.info(f"Sending battery charging request of {power} W")
        control_request("charge", power)
        return True

    def discharge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        _LOGGER.info(f"Sending battery discharging request of {power} W")
        control_request("discharge", power)
        return True

    def autocharge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        _LOGGER.info(f"Sending battery auto charging request")
        control_request("auto")
        return True

    hass.services.register("ferroamp", "charge", charge_battery)
    hass.services.register("ferroamp", "discharge", discharge_battery)
    hass.services.register("ferroamp", "autocharge", autocharge_battery)

    return True
