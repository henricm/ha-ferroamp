import uuid
from unittest.mock import call, patch

import pytest
from homeassistant.const import (
    CONF_NAME,
    CONF_PREFIX
)
from homeassistant.helpers import device_registry
from pytest_homeassistant_custom_component.common import async_fire_mqtt_message, MockConfigEntry

from custom_components.ferroamp import ATTR_POWER, ATTR_TARGET, async_setup
from custom_components.ferroamp.const import DOMAIN, CONF_INTERVAL, DATA_DEVICES, DATA_PREFIXES, DATA_LISTENERS


def mock_uuid():
    return uuid.UUID(int=1)


def create_config(name="Ferroamp", prefix="extapi", unique_id="ferroamp"):
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: name,
            CONF_PREFIX: prefix
        },
        options={
            CONF_INTERVAL: 1,
        },
        version=1,
        unique_id=unique_id,
    )


async def test_no_mqtt(hass, caplog):
    result = await async_setup(hass, {})
    assert not result
    assert "MQTT integration is not available" in caplog.text


async def test_unload(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/esm"
    msg = '{"id":{"val":"1"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await config_entry.async_unload(hass)
    await hass.async_block_till_done()

    assert hass.data[DOMAIN][DATA_DEVICES].get(config_entry.unique_id) is None
    assert hass.data[DOMAIN][DATA_PREFIXES].get(config_entry.unique_id) is None
    assert hass.data[DOMAIN][DATA_LISTENERS].get(config_entry.unique_id) is None
    assert hass.data[DOMAIN].get(config_entry.unique_id) is None


@patch('uuid.uuid1', mock_uuid)
async def test_service_charge(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "charge",
        {
            ATTR_POWER: 2000,
        },
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "extapi/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "charge", "arg": 2000}}',
            0,
            False
        )]
    )


@patch('uuid.uuid1', mock_uuid)
async def test_service_charge_default_power(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "charge",
        {},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "extapi/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "charge", "arg": 1000}}',
            0,
            False
        )]
    )


@patch('uuid.uuid1', mock_uuid)
async def test_service_discharge(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "discharge",
        {
            ATTR_POWER: 2000,
        },
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "extapi/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "discharge", "arg": 2000}}',
            0,
            False
        )]
    )


@patch('uuid.uuid1', mock_uuid)
async def test_service_discharge_default_power(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "discharge",
        {},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "extapi/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "discharge", "arg": 1000}}',
            0,
            False
        )]
    )


@patch('uuid.uuid1', mock_uuid)
async def test_service_autocharge(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        "autocharge",
        {},
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "extapi/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "auto"}}',
            0,
            False
        )]
    )


@patch('uuid.uuid1', mock_uuid)
async def test_multiple_configs_no_target(hass, mqtt_mock):
    config_entry1 = create_config()
    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    config_entry2 = create_config("Other", "other", "other")
    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN,
            "autocharge",
            {},
            blocking=True,
        )


@patch('uuid.uuid1', mock_uuid)
async def test_multiple_configs_target_not_found(hass, mqtt_mock):
    config_entry1 = create_config()
    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    config_entry2 = create_config("Other", "other", "other")
    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN,
            "autocharge",
            {
                ATTR_TARGET: "missing"
            },
            blocking=True,
        )


@patch('uuid.uuid1', mock_uuid)
async def test_multiple_configs_target_no_prefix_found(hass, mqtt_mock):
    config_entry1 = create_config()
    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    config_entry2 = create_config("Other", "other", "other")
    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    config_entry3 = MockConfigEntry(
        domain="light",
        data={
            CONF_PREFIX: None
        },
        version=1,
        entry_id="1234",
        unique_id="1234",
    )
    config_entry3.add_to_hass(hass)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()
    dr = device_registry.async_get(hass)
    dev = dr.async_get_or_create(
        config_entry_id="1234",
        connections={("ethernet", "12:34:56:78:90:AB:CD:EF")},
        identifiers={("bridgeid", "0123")},
        manufacturer="manufacturer",
        model="model",
    )

    with pytest.raises(Exception):
        await hass.services.async_call(
            DOMAIN,
            "autocharge",
            {
                ATTR_TARGET: dev.id
            },
            blocking=True,
        )


@patch('uuid.uuid1', mock_uuid)
async def test_multiple_configs_correct_prefix_is_used(hass, mqtt_mock):
    config_entry1 = create_config()
    config_entry1.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry1.entry_id)
    config_entry2 = create_config("Other", "other", "other")
    config_entry2.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry2.entry_id)
    await hass.async_block_till_done()

    msg = '{}'
    async_fire_mqtt_message(hass, "extapi/data/ehub", msg)
    async_fire_mqtt_message(hass, "other/data/ehub", msg)
    await hass.async_block_till_done()
    dr = device_registry.async_get(hass)
    dev = dr.async_get_or_create(
        config_entry_id=config_entry2.entry_id,
        identifiers={(DOMAIN, "other_ehub")},
    )

    await hass.services.async_call(
        DOMAIN,
        "autocharge",
        {
            ATTR_TARGET: dev.id
        },
        blocking=True,
    )

    mqtt_mock.async_publish.assert_has_calls(
        [call(
            "other/control/request",
            '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "auto"}}',
            0,
            False
        )]
    )
