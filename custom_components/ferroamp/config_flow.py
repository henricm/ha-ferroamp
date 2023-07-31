from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PREFIX
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify
import voluptuous as vol

from .const import CONF_INTERVAL, DOMAIN, MANUFACTURER

TOPIC_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=MANUFACTURER): cv.string,
        vol.Required(CONF_PREFIX, default="extapi"): cv.string,
    }
)


class FerroampConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Ferroamp config flow."""

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

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL,
                        default=interval,
                    ): cv.positive_int,
                }
            ),
            errors=errors,
        )
