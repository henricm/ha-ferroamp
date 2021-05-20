"""Ferroamp EnergyHub, SSO, ESO and ESM sensors"""

import json
import logging
import uuid

from homeassistant import config_entries, core
from homeassistant.const import CONF_NAME, CONF_PREFIX
from homeassistant.components import mqtt
from homeassistant.util import slugify

from .const import DATA_DEVICES, DATA_LISTENERS, DATA_PREFIXES, DOMAIN

CONTROL_REQUEST = "control/request"
ATTR_POWER = "power"
ATTR_TARGET = "target"
DEFAULT_POWER = 1000

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = entry.data
    hass.data[DOMAIN].setdefault(DATA_PREFIXES, {})
    hass.data[DOMAIN][DATA_PREFIXES][slugify(entry.data[CONF_NAME])] = entry.data[
        CONF_PREFIX
    ]

    # Forward the setup to the sensor platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    if await hass.config_entries.async_forward_entry_unload(entry, "sensor"):
        for unsubscribe_listener in hass.data[DOMAIN][DATA_LISTENERS][entry.unique_id]:
            unsubscribe_listener()
        config = hass.data[DOMAIN][DATA_DEVICES][entry.unique_id]
        for device in config.values():
            for sensor in device.values():
                sensor.async_remove()
        hass.data[DOMAIN][DATA_DEVICES].pop(entry.unique_id)
        hass.data[DOMAIN][DATA_PREFIXES].pop(slugify(entry.data[CONF_NAME]))
        hass.data[DOMAIN][DATA_LISTENERS].pop(entry.unique_id)
        return True
    return False


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    _LOGGER.debug("Setting up ferroamp battery service calls")
    hass.data.setdefault(DOMAIN, {})

    def control_request(cmd_name, target, power=None):
        prefix = list(hass.data[DOMAIN][DATA_PREFIXES].values())[0]
        if len(hass.data[DOMAIN][DATA_PREFIXES]) > 1:
            if len(target) == 0:
                raise Exception(f"Target needs to be specified since more than one instance of Ferroamp is available")
            _LOGGER.info(f"Looking up prefix for {target}")
            prefix = hass.data[DOMAIN][DATA_PREFIXES].get(slugify(target))
            _LOGGER.info(f"Prefix for {target} is {prefix}")
            if prefix is None:
                raise Exception(f"No prefix found for {target}")

        cmd = {"name": cmd_name}
        if power is not None:
            cmd["arg"] = power

        payload = {"transId": str(uuid.uuid1()), "cmd": cmd}

        _LOGGER.info(
            f"Sending control request {cmd} with payload {payload} to {prefix}/{CONTROL_REQUEST}"
        )

        mqtt.async_publish(hass, f"{prefix}/{CONTROL_REQUEST}", json.dumps(payload))

    def charge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery charging request of {power} W to {target}")
        control_request("charge", target, power)

    def discharge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery discharging request of {power} W to {target}")
        control_request("discharge", target, power)

    def autocharge_battery(call):
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery auto charging request to {target}")
        control_request("auto", target)

    hass.services.async_register(DOMAIN, "charge", charge_battery)
    hass.services.async_register(DOMAIN, "discharge", discharge_battery)
    hass.services.async_register(DOMAIN, "autocharge", autocharge_battery)

    return True
