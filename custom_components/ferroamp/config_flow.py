from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PREFIX
from homeassistant.core import callback
from homeassistant.util import slugify

from .const import (
    CONF_INTERVAL,
    CONF_PRECISION_BATTERY,
    CONF_PRECISION_CURRENT,
    CONF_PRECISION_FREQUENCY,
    CONF_PRECISION_ENERGY,
    CONF_PRECISION_TEMPERATURE,
    CONF_PRECISION_VOLTAGE,
    DOMAIN,
    MANUFACTURER
)

TOPIC_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=MANUFACTURER): cv.string,
    vol.Required(CONF_PREFIX, default="extapi"): cv.string
})


class FerroampConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ferroammp config flow."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            if len(user_input.get(CONF_NAME)) == 0:
                errors["base"] = "name"
            elif len(user_input.get(CONF_PREFIX)) == 0:
                errors["base"] = "prefix"
            await self.async_set_unique_id(slugify(user_input[CONF_NAME]))
            self._abort_if_unique_id_configured()
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=TOPIC_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return FerroampOptionsFlowHandler(config_entry)


class FerroampOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        interval = self.config_entry.options.get(CONF_INTERVAL)
        if interval is None or interval == 0:
            interval = 30

        precision_battery = self.config_entry.options.get(CONF_PRECISION_BATTERY)
        if precision_battery is None:
            precision_battery = 1

        precision_current = self.config_entry.options.get(CONF_PRECISION_CURRENT)
        if precision_current is None:
            precision_current = 0

        precision_energy = self.config_entry.options.get(CONF_PRECISION_ENERGY)
        if precision_energy is None:
            precision_energy = 1

        precision_frequency = self.config_entry.options.get(CONF_PRECISION_FREQUENCY)
        if precision_frequency is None:
            precision_frequency = 2

        precision_temperature = self.config_entry.options.get(CONF_PRECISION_TEMPERATURE)
        if precision_temperature is None:
            precision_temperature = 0

        precision_voltage = self.config_entry.options.get(CONF_PRECISION_VOLTAGE)
        if precision_voltage is None:
            precision_voltage = 0

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL,
                        default=interval,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_BATTERY,
                        default=precision_battery,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_CURRENT,
                        default=precision_current,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_ENERGY,
                        default=precision_energy,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_FREQUENCY,
                        default=precision_frequency,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_TEMPERATURE,
                        default=precision_temperature,
                    ): cv.positive_int,
                    vol.Required(
                        CONF_PRECISION_VOLTAGE,
                        default=precision_voltage,
                    ): cv.positive_int
                }
            ),
            errors=errors
        )
