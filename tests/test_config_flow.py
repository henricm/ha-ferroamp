from unittest import mock

from homeassistant import data_entry_flow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ferroamp import CONF_NAME, CONF_PREFIX, config_flow
from custom_components.ferroamp.const import CONF_INTERVAL


async def test_flow_user_init(hass, mqtt_mock):
    """Test the initialization of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    expected = {
        "data_schema": config_flow.TOPIC_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": mock.ANY,
        "handler": "ferroamp",
        "step_id": "user",
        "type": "form",
        "last_step": None,
    }
    assert all(
        [
            expected_value == result[key]
            for key, expected_value in expected.items()
            if key != "preview"
        ]
    )


async def test_flow_user_step_no_input(hass, mqtt_mock):
    """Test appropriate error when no input is provided."""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_NAME: "", CONF_PREFIX: ""}
    )
    assert {"base": "name"} == result["errors"]


async def test_flow_user_creates_config_entry(hass, mqtt_mock):
    """Test the config entry is successfully created."""
    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={}
    )
    expected = {
        "version": 1,
        "type": "create_entry",
        "flow_id": mock.ANY,
        "handler": "ferroamp",
        "options": {},
        "title": "Ferroamp",
        "data": {
            "name": "Ferroamp",
            "prefix": "extapi",
        },
        "description": None,
        "description_placeholders": None,
        "result": mock.ANY,
    }

    assert expected == {
        k: v for k, v in result.items() if k != "context" and k != "minor_version"
    }
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_options_flow(hass, mqtt_mock):
    """Test config flow options."""
    config_entry = MockConfigEntry(
        domain=config_flow.DOMAIN,
        unique_id="ferroamp",
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi",
        },
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    # show initial form
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert "form" == result["type"]
    assert "init" == result["step_id"]
    assert {} == result["errors"]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_INTERVAL: 20,
        },
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["data"] == {
        CONF_INTERVAL: 20,
    }
    assert config_entry.data == {CONF_NAME: "Ferroamp", CONF_PREFIX: "extapi"}
    assert config_entry.options == {
        CONF_INTERVAL: 20,
    }
