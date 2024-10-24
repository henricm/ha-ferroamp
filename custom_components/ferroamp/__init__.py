"""Ferroamp EnergyHub, SSO, ESO and ESM sensors"""

import json
import logging
import uuid

from homeassistant import config_entries, core
from homeassistant.components import mqtt
from homeassistant.const import CONF_NAME, CONF_PREFIX
from homeassistant.helpers import device_registry as dr
from homeassistant.util import slugify

from .const import DATA_DEVICES, DATA_LISTENERS, DATA_PREFIXES, DOMAIN, PLATFORMS

CONTROL_REQUEST = "control/request"
ATTR_POWER = "power"
ATTR_TARGET = "target"
DEFAULT_POWER = 1000

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up integration from ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.unique_id] = entry.data
    hass.data[DOMAIN].setdefault(DATA_PREFIXES, {})
    hass.data[DOMAIN][DATA_PREFIXES][slugify(entry.data[CONF_NAME])] = entry.data[
        CONF_PREFIX
    ]

    # Forward setup to the platforms.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
):
    """Unload a config entry."""

    # Forward unload to the platforms.
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        for unsubscribe_listener in hass.data[DOMAIN][DATA_LISTENERS][entry.unique_id]:
            unsubscribe_listener()
        hass.data[DOMAIN][DATA_DEVICES].pop(entry.unique_id)
        hass.data[DOMAIN][DATA_PREFIXES].pop(slugify(entry.data[CONF_NAME]))
        hass.data[DOMAIN][DATA_LISTENERS].pop(entry.unique_id)
        hass.data[DOMAIN].pop(entry.unique_id)
    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    # Make sure MQTT is available and the entry component is loaded
    entries = hass.config_entries.async_entries(mqtt.DOMAIN)
    if len(entries) == 0:
        _LOGGER.error("MQTT integration is not available")
        return False
    if not await hass.config_entries.async_wait_component(entries[0]):
        if len(entries) > 1:
            _LOGGER.warn(
                "Multiple MQTT integrations entries available, please check your configuration"
            )
        _LOGGER.error("MQTT integration component is not loaded")
        return False

    _LOGGER.debug("Setting up ferroamp battery service calls")
    hass.data.setdefault(DOMAIN, {})
    device_registry = dr.async_get(hass)

    async def control_request(cmd_name, target, power=None):
        prefix = list(hass.data[DOMAIN][DATA_PREFIXES].values())[0]
        if len(hass.data[DOMAIN][DATA_PREFIXES]) > 1:
            if len(target) == 0:
                raise Exception(
                    "Target needs to be specified since more than one instance of Ferroamp is available"
                )
            _LOGGER.info(f"Looking up prefix for device with id {target}")
            device = device_registry.async_get(target)
            if device is None:
                raise Exception(f"Device with id {target} not found")

            prefix = None
            for c in device.config_entries:
                prefix = hass.config_entries.async_get_entry(c).data[CONF_PREFIX]
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

        await mqtt.async_publish(
            hass, f"{prefix}/{CONTROL_REQUEST}", json.dumps(payload)
        )

    async def charge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery charging request of {power} W to {target}")
        await control_request("charge", target, power)

    async def discharge_battery(call):
        power = call.data.get(ATTR_POWER, DEFAULT_POWER)
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery discharging request of {power} W to {target}")
        await control_request("discharge", target, power)

    async def autocharge_battery(call):
        target = call.data.get(ATTR_TARGET, "")
        _LOGGER.info(f"Sending battery auto charging request to {target}")
        await control_request("auto", target)

    hass.services.async_register(DOMAIN, "charge", charge_battery)
    hass.services.async_register(DOMAIN, "discharge", discharge_battery)
    hass.services.async_register(DOMAIN, "autocharge", autocharge_battery)

    return True
