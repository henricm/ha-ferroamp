import uuid
from unittest.mock import patch
import unittest

import pytest
from homeassistant.const import (
    CONF_NAME,
    CONF_PREFIX
)
from homeassistant.core import CoreState, State
from homeassistant.helpers import entity_registry
from pytest_homeassistant_custom_component.common import async_fire_mqtt_message, MockConfigEntry, mock_restore_cache

from custom_components.ferroamp.const import (
    DOMAIN,
    CONF_INTERVAL,
    CONF_PRECISION_BATTERY,
    CONF_PRECISION_CURRENT,
    CONF_PRECISION_ENERGY,
    CONF_PRECISION_FREQUENCY,
    CONF_PRECISION_TEMPERATURE,
    CONF_PRECISION_VOLTAGE,
    DATA_DEVICES
)
from custom_components.ferroamp.sensor import (
    BatteryFerroampSensor,
    EnergyFerroampSensor,
    KeyedFerroampSensor,
    StringValFerroampSensor,
    TemperatureFerroampSensor,
    VoltageFerroampSensor
)


def mock_uuid():
    return uuid.UUID(int=1)


def create_config():
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi"
        },
        options={
            CONF_INTERVAL: 0,
        },
        version=1,
        unique_id="ferroamp",
    )


async def test_setting_ehub_sensor_values_via_mqtt_message(hass, mqtt_mock):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi"
        },
        options={
            CONF_INTERVAL: 1,
            CONF_PRECISION_BATTERY: 0,
            CONF_PRECISION_CURRENT: 0,
            CONF_PRECISION_ENERGY: 0,
            CONF_PRECISION_FREQUENCY: 0,
            CONF_PRECISION_TEMPERATURE: 0,
            CONF_PRECISION_VOLTAGE: 0,
        },
        version=1,
        unique_id="ferroamp",
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    er = entity_registry.async_get(hass)
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-ul', config_entry=config_entry,
        suggested_object_id="ferroamp_external_voltage")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-il', config_entry=config_entry,
        suggested_object_id="ferroamp_inverter_rms_current")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-gridfreq', config_entry=config_entry,
        suggested_object_id="ferroamp_estimated_grid_frequency")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-pext', config_entry=config_entry,
        suggested_object_id="ferroamp_grid_power")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-wextprodq', config_entry=config_entry,
        suggested_object_id="ferroamp_external_energy_produced")

    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = """{
                "wloadconsq": {"L2": "5509231063416", "L3": "10852247351438", "L1": "7902091810549"},
                "iloadd": {"L2": "-0.67", "L3": "0.56", "L1": "1.55"},
                "wextconsq": {"L2": "5364952651263", "L3": "10118502962305", "L1": "7277915408026"},
                "ppv": {"val": "10107.51"},
                "iext": {"L2": "8.90", "L3": "7.49", "L1": "7.59"},
                "iloadq": {"L2": "1.16", "L3": "3.61", "L1": "3.89"},
                "iace": {"L2": "0.00", "L3": "0.00", "L1": "0.00"},
                "ul": {"L2": "233.81", "L3": "231.18", "L1": "228.81"},
                "pinvreactive": {"L2": "438.12", "L3": "444.64", "L1": "430.37"},
                "ts": {"val": "2021-03-08T08:43:12UTC"},
                "ploadreactive": {"L2": "-110.77", "L3": "91.54", "L1": "250.78"},
                "state": {"val": "4097"},
                "wloadprodq": {"L2": "18020837409", "L3": "8433745", "L1": "4976003"},
                "iavbl": {"L2": "26.31", "L3": "29.69", "L1": "31.20"},
                "pinv": {"L2": "-2263.35", "L3": "-2234.62", "L1": "-2224.66"},
                "iextq": {"L2": "-12.53", "L3": "-10.06", "L1": "-9.86"},
                "pext": {"L2": "-2071.57", "L3": "-1644.50", "L1": "-1595.28"},
                "wbatcons": {"val": "4472794198593"},
                "wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"},
                "wpv": {"val": "4422089590383"},
                "winvconsq": {"L2": "1475109889749", "L3": "1451934095829", "L1": "1436427014025"},
                "pextreactive": {"L2": "327.35", "L3": "536.18", "L1": "681.15"},
                "udc": {"neg": "-383.96", "pos": "384.31"},
                "sext": {"val": "5549.12"},
                "pbat": {"val": "-3218.99"},
                "iextd": {"L2": "1.98", "L3": "3.28", "L1": "4.21"},
                "iavblq_3p": {"val": "29.05"},
                "wbatprod": {"val": "4918944968551"},
                "iavblq": {"L2": "29.05", "L3": "33.93", "L1": "35.89"},
                "ild": {"L2": "2.65", "L3": "2.72", "L1": "2.66"},
                "gridfreq": {"val": "50.07"},
                "pload": {"L2": "191.78", "L3": "590.12", "L1": "629.38"},
                "ilq": {"L2": "-13.69", "L3": "-13.67", "L1": "-13.75"},
                "winvprodq": {"L2": "2610825033980", "L3": "2570987302422", "L1": "2567078340545"},
                "il": {"L2": "9.85", "L3": "9.85", "L1": "9.89"},
                "soc":{"val":"79.9"},
                "soh":{"val":"98.9"},
                "ratedcap":{"val":"15300"}}"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_external_voltage")
    assert state.state == "694"
    assert state.attributes == {
        'L1': 228.81,
        'L2': 233.81,
        'L3': 231.18,
        'device_class': 'voltage',
        'friendly_name': 'EnergyHub External Voltage',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }

    state = hass.states.get("sensor.ferroamp_inverter_rms_current")
    assert state.state == "30"
    assert state.attributes == {
        'L1': 9.89,
        'L2': 9.85,
        'L3': 9.85,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Inverter RMS current',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_inverter_rms_current_l1")
    assert state.state == "10"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'EnergyHub Inverter RMS current L1',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_inverter_rms_current_l2")
    assert state.state == "10"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'EnergyHub Inverter RMS current L2',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_inverter_rms_current_l3")
    assert state.state == "10"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'EnergyHub Inverter RMS current L3',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_inverter_reactive_current")
    assert state.state == "8"
    assert state.attributes == {
        'L1': 2.66,
        'L2': 2.65,
        'L3': 2.72,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Inverter reactive current',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_grid_current")
    assert state.state == "24"
    assert state.attributes == {
        'L1': 7.59,
        'L2': 8.9,
        'L3': 7.49,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Grid Current',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_estimated_grid_frequency")
    assert state.state == "50"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Estimated Grid Frequency',
        'icon': 'mdi:sine-wave',
        'unit_of_measurement': 'Hz'
    }

    state = hass.states.get("sensor.ferroamp_grid_reactive_current")
    assert state.state == "9"
    assert state.attributes == {
        'L1': 4.21,
        'L2': 1.98,
        'L3': 3.28,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Grid Reactive Current',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_external_active_current")
    assert state.state == "-32"
    assert state.attributes == {
        'L1': -9.86,
        'L2': -12.53,
        'L3': -10.06,
        'device_class': 'current',
        'friendly_name': 'EnergyHub External Active Current',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_adaptive_current_equalization")
    assert state.state == "0"
    assert state.attributes == {
        'L1': 0,
        'L2': 0,
        'L3': 0,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Adaptive Current Equalization',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_grid_power")
    assert state.state == "-5311"
    assert state.attributes == {
        'L1': -1595.28,
        'L2': -2071.57,
        'L3': -1644.5,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Grid Power',
        'icon': 'mdi:transmission-tower',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_grid_power_reactive")
    assert state.state == "1545"
    assert state.attributes == {
        'L1': 681.15,
        'L2': 327.35,
        'L3': 536.18,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Grid Power Reactive',
        'icon': 'mdi:transmission-tower',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_inverter_power_active")
    assert state.state == "-6723"
    assert state.attributes == {
        'L1': -2224.66,
        'L2': -2263.35,
        'L3': -2234.62,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Inverter Power, active',
        'icon': 'mdi:solar-power',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_inverter_power_reactive")
    assert state.state == "1313"
    assert state.attributes == {
        'L1': 430.37,
        'L2': 438.12,
        'L3': 444.64,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Inverter Power, reactive',
        'icon': 'mdi:solar-power',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_consumption_power")
    assert state.state == "1411"
    assert state.attributes == {
        'L1': 629.38,
        'L2': 191.78,
        'L3': 590.12,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Consumption Power',
        'icon': 'mdi:power-plug',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_consumption_power_reactive")
    assert state.state == "232"
    assert state.attributes == {
        'L1': 250.78,
        'L2': -110.77,
        'L3': 91.54,
        'device_class': 'power',
        'friendly_name': 'EnergyHub Consumption Power Reactive',
        'icon': 'mdi:power-plug',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_external_energy_produced")
    assert state.state == "662"
    assert state.attributes == {
        'L1': 183.92,
        'L2': 310.57,
        'L3': 167.93,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub External Energy Produced',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_external_energy_consumed")
    assert state.state == "6323"
    assert state.attributes == {
        'L1': 2021.64,
        'L2': 1490.26,
        'L3': 2810.7,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub External Energy Consumed',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_inverter_energy_produced")
    assert state.state == "2152"
    assert state.attributes == {
        'L1': 713.08,
        'L2': 725.23,
        'L3': 714.16,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Inverter Energy Produced',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_inverter_energy_consumed")
    assert state.state == "1212"
    assert state.attributes == {
        'L1': 399.01,
        'L2': 409.75,
        'L3': 403.32,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Inverter Energy Consumed',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_load_energy_produced")
    assert state.state == "5"
    assert state.attributes == {
        'L1': 0.0,
        'L2': 5.01,
        'L3': 0.0,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Load Energy Produced',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_load_energy_consumed")
    assert state.state == "6740"
    assert state.attributes == {
        'L1': 2195.03,
        'L2': 1530.34,
        'L3': 3014.51,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Load Energy Consumed',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_total_solar_energy")
    assert state.state == "1228"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Total Solar Energy',
        'icon': 'mdi:solar-power',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_battery_energy_produced")
    assert state.state == "1366"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Battery Energy Produced',
        'icon': 'mdi:battery-plus',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_battery_energy_consumed")
    assert state.state == "1242"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'EnergyHub Battery Energy Consumed',
        'icon': 'mdi:battery-minus',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_system_state")
    assert state.state == "4097"
    assert state.attributes == {
        'friendly_name': 'EnergyHub System State',
        'icon': 'mdi:traffic-light',
        'unit_of_measurement': ''
    }

    state = hass.states.get("sensor.ferroamp_dc_link_voltage")
    assert state.state == "768.27"
    assert state.attributes == {
        'device_class': 'voltage',
        'friendly_name': 'EnergyHub DC Link Voltage',
        'icon': 'mdi:current-ac',
        'neg': -383.96,
        'pos': 384.31,
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }

    state = hass.states.get("sensor.ferroamp_system_state_of_charge")
    assert state.state == "80"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'EnergyHub System State of Charge',
        'icon': 'mdi:battery-80',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_system_state_of_health")
    assert state.state == "99"
    assert state.attributes == {
        'friendly_name': 'EnergyHub System State of Health',
        'icon': 'mdi:battery-90',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_apparent_power")
    assert state.state == "5549"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Apparent power',
        'icon': 'mdi:transmission-tower',
        'unit_of_measurement': 'VA'
    }

    state = hass.states.get("sensor.ferroamp_solar_power")
    assert state.state == "10108"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'EnergyHub Solar Power',
        'icon': 'mdi:solar-power',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_battery_power")
    assert state.state == "-3219"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'EnergyHub Battery Power',
        'icon': 'mdi:battery',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_total_rated_capacity_of_all_batteries")
    assert state.state == "15300"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Total rated capacity of all batteries',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'Wh'
    }

    state = hass.states.get("sensor.ferroamp_available_active_current_for_load_balancing")
    assert state.state == "29"
    assert state.attributes == {
        'L1': 35.89,
        'L2': 29.05,
        'L3': 33.93,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Available active current for load balancing',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_available_rms_current_for_load_balancing")
    assert state.state == "26"
    assert state.attributes == {
        'L1': 31.20,
        'L2': 26.31,
        'L3': 29.69,
        'device_class': 'current',
        'friendly_name': 'EnergyHub Available RMS current for load balancing',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_available_three_phase_active_current_for_load_balancing")
    assert state.state == "29"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'EnergyHub Available three phase active current for load balancing',
        'icon': 'mdi:current-ac',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }


async def test_only_adding_load_balancing_sensors_if_present_in_message(hass, mqtt_mock):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi"
        },
        options={
            CONF_INTERVAL: 1,
            CONF_PRECISION_BATTERY: 0,
            CONF_PRECISION_CURRENT: 0,
            CONF_PRECISION_ENERGY: 0,
            CONF_PRECISION_FREQUENCY: 0,
            CONF_PRECISION_TEMPERATURE: 0,
            CONF_PRECISION_VOLTAGE: 0,
        },
        version=1,
        unique_id="ferroamp",
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    er = entity_registry.async_get(hass)
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-ul', config_entry=config_entry,
        suggested_object_id="ferroamp_external_voltage")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-il', config_entry=config_entry,
        suggested_object_id="ferroamp_inverter_rms_current")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-gridfreq', config_entry=config_entry,
        suggested_object_id="ferroamp_estimated_grid_frequency")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-pext', config_entry=config_entry,
        suggested_object_id="ferroamp_grid_power")
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-wextprodq', config_entry=config_entry,
        suggested_object_id="ferroamp_external_energy_produced")

    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = """{
                "wloadconsq": {"L2": "5509231063416", "L3": "10852247351438", "L1": "7902091810549"},
                "iloadd": {"L2": "-0.67", "L3": "0.56", "L1": "1.55"},
                "wextconsq": {"L2": "5364952651263", "L3": "10118502962305", "L1": "7277915408026"},
                "ppv": {"val": "10107.51"},
                "iext": {"L2": "8.90", "L3": "7.49", "L1": "7.59"},
                "iloadq": {"L2": "1.16", "L3": "3.61", "L1": "3.89"},
                "iace": {"L2": "0.00", "L3": "0.00", "L1": "0.00"},
                "ul": {"L2": "233.81", "L3": "231.18", "L1": "228.81"},
                "pinvreactive": {"L2": "438.12", "L3": "444.64", "L1": "430.37"},
                "ts": {"val": "2021-03-08T08:43:12UTC"},
                "ploadreactive": {"L2": "-110.77", "L3": "91.54", "L1": "250.78"},
                "state": {"val": "4097"},
                "wloadprodq": {"L2": "18020837409", "L3": "8433745", "L1": "4976003"},
                "pinv": {"L2": "-2263.35", "L3": "-2234.62", "L1": "-2224.66"},
                "iextq": {"L2": "-12.53", "L3": "-10.06", "L1": "-9.86"},
                "pext": {"L2": "-2071.57", "L3": "-1644.50", "L1": "-1595.28"},
                "wbatcons": {"val": "4472794198593"},
                "wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"},
                "wpv": {"val": "4422089590383"},
                "winvconsq": {"L2": "1475109889749", "L3": "1451934095829", "L1": "1436427014025"},
                "pextreactive": {"L2": "327.35", "L3": "536.18", "L1": "681.15"},
                "udc": {"neg": "-383.96", "pos": "384.31"},
                "sext": {"val": "5549.12"},
                "pbat": {"val": "-3218.99"},
                "iextd": {"L2": "1.98", "L3": "3.28", "L1": "4.21"},
                "wbatprod": {"val": "4918944968551"},
                "ild": {"L2": "2.65", "L3": "2.72", "L1": "2.66"},
                "gridfreq": {"val": "50.07"},
                "pload": {"L2": "191.78", "L3": "590.12", "L1": "629.38"},
                "ilq": {"L2": "-13.69", "L3": "-13.67", "L1": "-13.75"},
                "winvprodq": {"L2": "2610825033980", "L3": "2570987302422", "L1": "2567078340545"},
                "il": {"L2": "9.85", "L3": "9.85", "L1": "9.89"},
                "soc":{"val":"79.9"},
                "soh":{"val":"98.9"},
                "ratedcap":{"val":"15300"}}"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_available_active_current_for_load_balancing")
    assert state is None

    state = hass.states.get("sensor.ferroamp_available_rms_current_for_load_balancing")
    assert state is None

    state = hass.states.get("sensor.ferroamp_available_three_phase_active_current_for_load_balancing")
    assert state is None


async def test_only_adding_battery_specific_sensors_if_present_in_mqtt_message(hass, mqtt_mock):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi"
        },
        options={
            CONF_INTERVAL: 1,
            CONF_PRECISION_BATTERY: 0,
            CONF_PRECISION_CURRENT: 0,
            CONF_PRECISION_ENERGY: 0,
            CONF_PRECISION_FREQUENCY: 0,
            CONF_PRECISION_TEMPERATURE: 0,
            CONF_PRECISION_VOLTAGE: 0,
        },
        version=1,
        unique_id="ferroamp",
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    er = entity_registry.async_get(hass)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = """{
                "wloadconsq": {"L2": "5509231063416", "L3": "10852247351438", "L1": "7902091810549"},
                "iloadd": {"L2": "-0.67", "L3": "0.56", "L1": "1.55"},
                "wextconsq": {"L2": "5364952651263", "L3": "10118502962305", "L1": "7277915408026"},
                "ppv": {"val": "10107.51"},
                "iext": {"L2": "8.90", "L3": "7.49", "L1": "7.59"},
                "iloadq": {"L2": "1.16", "L3": "3.61", "L1": "3.89"},
                "iace": {"L2": "0.00", "L3": "0.00", "L1": "0.00"},
                "ul": {"L2": "233.81", "L3": "231.18", "L1": "228.81"},
                "pinvreactive": {"L2": "438.12", "L3": "444.64", "L1": "430.37"},
                "ts": {"val": "2021-03-08T08:43:12UTC"},
                "ploadreactive": {"L2": "-110.77", "L3": "91.54", "L1": "250.78"},
                "state": {"val": "4097"},
                "wloadprodq": {"L2": "18020837409", "L3": "8433745", "L1": "4976003"},
                "iavbl": {"L2": "26.31", "L3": "29.69", "L1": "31.20"},
                "pinv": {"L2": "-2263.35", "L3": "-2234.62", "L1": "-2224.66"},
                "iextq": {"L2": "-12.53", "L3": "-10.06", "L1": "-9.86"},
                "pext": {"L2": "-2071.57", "L3": "-1644.50", "L1": "-1595.28"},
                "wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"},
                "wpv": {"val": "4422089590383"},
                "winvconsq": {"L2": "1475109889749", "L3": "1451934095829", "L1": "1436427014025"},
                "pextreactive": {"L2": "327.35", "L3": "536.18", "L1": "681.15"},
                "udc": {"neg": "-383.96", "pos": "384.31"},
                "sext": {"val": "5549.12"},
                "iextd": {"L2": "1.98", "L3": "3.28", "L1": "4.21"},
                "iavblq_3p": {"val": "29.05"},
                "iavblq": {"L2": "29.05", "L3": "33.93", "L1": "35.89"},
                "ild": {"L2": "2.65", "L3": "2.72", "L1": "2.66"},
                "gridfreq": {"val": "50.07"},
                "pload": {"L2": "191.78", "L3": "590.12", "L1": "629.38"},
                "ilq": {"L2": "-13.69", "L3": "-13.67", "L1": "-13.75"},
                "winvprodq": {"L2": "2610825033980", "L3": "2570987302422", "L1": "2567078340545"},
                "il": {"L2": "9.85", "L3": "9.85", "L1": "9.89"}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_battery_energy_produced")
    assert state is None

    state = hass.states.get("sensor.ferroamp_battery_energy_consumed")
    assert state is None

    state = hass.states.get("sensor.ferroamp_system_state_of_charge")
    assert state is None

    state = hass.states.get("sensor.ferroamp_system_state_of_health")
    assert state is None

    state = hass.states.get("sensor.ferroamp_battery_power")
    assert state is None

    state = hass.states.get("sensor.ferroamp_total_rated_capacity_of_all_batteries")
    assert state is None


async def test_setting_esm_sensor_values_via_mqtt_message(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/esm"
    msg = """{
        "id":{"val":"1"},
        "soh":{"val":"89.2"},
        "soc":{"val":"45.5"},
        "ratedCapacity":{"val":"15300"},
        "ratedPower":{"val":"7000"},
        "status":{"val":"0"}
    }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_1_state_of_health")
    assert state.state == "89.2"
    assert state.attributes == {
        'friendly_name': 'ESM 1 State of Health',
        'icon': 'mdi:battery-80',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_esm_1_state_of_charge")
    assert state.state == "45.5"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESM 1 State of Charge',
        'icon': 'mdi:battery-40',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_esm_1_rated_capacity")
    assert state.state == "15300"
    assert state.attributes == {
        'friendly_name': 'ESM 1 Rated Capacity',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'Wh'
    }

    state = hass.states.get("sensor.ferroamp_esm_1_rated_power")
    assert state.state == "7000"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'ESM 1 Rated Power',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_esm_1_status")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'ESM 1 Status',
        'icon': 'mdi:traffic-light',
        'unit_of_measurement': ''
    }


async def test_battery_full(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/esm"
    msg = '{"id":{"val":"1"},"soh":{"val":"89.2"},"soc":{"val":"100.0"},"ratedCapacity":{"val":"15300"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_1_state_of_charge")
    assert state.state == "100.0"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESM 1 State of Charge',
        'icon': 'mdi:battery',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_esm_1_rated_capacity")
    assert state.state == "15300"
    assert state.attributes == {
        'friendly_name': 'ESM 1 Rated Capacity',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'Wh'
    }


async def test_trim_part_no_from_esm_id(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/esm"
    msg = """{
        "id":{"val":"ES01Z000012345678 "},
        "soh":{"val":"89.2"},
        "soc":{"val":"45.5"},
        "ratedCapacity":{"val":"15300"},
        "ratedPower":{"val":"7000"},
        "status":{"val":"0"}
    }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_12345678_state_of_health")
    assert state.state == "89.2"
    assert state.attributes == {
        'friendly_name': 'ESM 12345678 State of Health',
        'icon': 'mdi:battery-80',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_esm_12345678_state_of_charge")
    assert state.state == "45.5"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESM 12345678 State of Charge',
        'icon': 'mdi:battery-40',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_esm_12345678_rated_capacity")
    assert state.state == "15300"
    assert state.attributes == {
        'friendly_name': 'ESM 12345678 Rated Capacity',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'Wh'
    }

    state = hass.states.get("sensor.ferroamp_esm_12345678_rated_power")
    assert state.state == "7000"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'ESM 12345678 Rated Power',
        'icon': 'mdi:battery',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_esm_12345678_status")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'ESM 12345678 Status',
        'icon': 'mdi:traffic-light',
        'unit_of_measurement': ''
    }

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_esm_12345678_status")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_esm_12345678"][entity.unique_id]
    assert isinstance(sensor, StringValFerroampSensor)
    assert sensor.device_info.get("model") == "ES01Z0000"


async def test_esm_trim_trailing_dash_from_model(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/esm"
    msg = """{
        "id":{"val":"30-H022-21030023"},
        "soh":{"val":"89.2"},
        "soc":{"val":"45.5"},
        "ratedCapacity":{"val":"15300"},
        "ratedPower":{"val":"7000"},
        "status":{"val":"0"}
    }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_21030023_state_of_health")
    assert state

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_esm_21030023_status")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_esm_21030023"][entity.unique_id]
    assert isinstance(sensor, StringValFerroampSensor)
    assert sensor.device_info.get("model") == "30-H022"


async def test_migrate_old_esm_entities(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_esm_ES01Z000012345678 -soh', config_entry=config_entry)

    topic = "extapi/data/esm"
    msg = """{
        "id":{"val":"ES01Z000012345678 "},
        "soh":{"val":"89.2"},
        "soc":{"val":"45.5"},
        "ratedCapacity":{"val":"15300"},
        "ratedPower":{"val":"7000"},
        "status":{"val":"0"}
    }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get(entity.entity_id)
    assert state.state == "89.2"
    assert state.attributes == {
        'friendly_name': 'ESM 12345678 State of Health',
        'icon': 'mdi:battery-80',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }


async def test_migrate_only_esm_entities_that_needs_migrating(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_esm_12345678-soh', config_entry=config_entry)

    topic = "extapi/data/esm"
    msg = """{
        "id":{"val":"12345678"},
        "soh":{"val":"89.2"},
        "soc":{"val":"45.5"},
        "ratedCapacity":{"val":"15300"},
        "ratedPower":{"val":"7000"},
        "status":{"val":"0"}
    }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get(entity.entity_id)
    assert state.state == "89.2"
    assert state.attributes == {
        'friendly_name': 'ESM 12345678 State of Health',
        'icon': 'mdi:battery-80',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }


async def test_setting_eso_sensor_values_via_mqtt_message(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/eso"
    msg = """{
            "soc": {"val": 48.100003999999998},
            "temp": {"val": 20.379000000000001},
            "wbatcons": {"val": 2213535479518},
            "ubat": {"val": 622.601},
            "ibat": {"val": 1.5700000000000001},
            "relaystatus": {"val": "0"},
            "faultcode": {"val": "80"},
            "ts": {"val": "2021-03-07T19:21:04UTC"},
            "id": {"val": "1"},
            "wbatprod": {"val": 2465106122063}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_eso_1_battery_voltage")
    assert state.state == "623"
    assert state.attributes == {
        'device_class': 'voltage',
        'friendly_name': 'ESO 1 Battery Voltage',
        'icon': 'mdi:battery',
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_battery_current")
    assert state.state == "2"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'ESO 1 Battery Current',
        'icon': 'mdi:battery',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_battery_power")
    assert state.state == "977"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'ESO 1 Battery Power',
        'icon': 'mdi:battery',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_total_energy_produced")
    assert state.state == "684.8"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'ESO 1 Total Energy Produced',
        'icon': 'mdi:battery-plus',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_total_energy_consumed")
    assert state.state == "614.9"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'ESO 1 Total Energy Consumed',
        'icon': 'mdi:battery-minus',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_state_of_charge")
    assert state.state == "48.1"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESO 1 State of Charge',
        'icon': 'mdi:battery-40',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_faultcode")
    assert state.state == "80"
    assert state.attributes == {
        'friendly_name': 'ESO 1 Faultcode',
        'icon': 'mdi:traffic-light',
        8: 'Not a fault, just an indication that Battery Manufacturer is not Ferroamp'
    }

    state = hass.states.get("sensor.ferroamp_eso_1_relay_status")
    assert state.state == "closed"
    assert state.attributes == {
        'friendly_name': 'ESO 1 Relay Status',
        'icon': '',
    }

    state = hass.states.get("sensor.ferroamp_eso_1_pcb_temperature")
    assert state.state == "20"
    assert state.attributes == {
        'device_class': 'temperature',
        'friendly_name': 'ESO 1 PCB Temperature',
        'icon': 'mdi:thermometer',
        'state_class': 'measurement',
        'unit_of_measurement': '°C'
    }


async def test_relay_status_open(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/eso"
    msg = """{
            "soc": {"val": 48.100003999999998},
            "temp": {"val": 20.379000000000001},
            "wbatcons": {"val": 2213535479518},
            "ubat": {"val": 622.601},
            "ibat": {"val": 1.5700000000000001},
            "relaystatus": {"val": "1"},
            "faultcode": {"val": "80"},
            "ts": {"val": "2021-03-07T19:21:04UTC"},
            "id": {"val": "1"},
            "wbatprod": {"val": 2465106122063}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_eso_1_relay_status")
    assert state.state == "open/disconnected"


async def test_relay_status_precharge(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/eso"
    msg = """{
            "soc": {"val": 48.100003999999998},
            "temp": {"val": 20.379000000000001},
            "wbatcons": {"val": 2213535479518},
            "ubat": {"val": 622.601},
            "ibat": {"val": 1.5700000000000001},
            "relaystatus": {"val": "2"},
            "faultcode": {"val": "80"},
            "ts": {"val": "2021-03-07T19:21:04UTC"},
            "id": {"val": "1"},
            "wbatprod": {"val": 2465106122063}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_eso_1_relay_status")
    assert state.state == "precharge"


async def test_ignore_eso_message_without_id(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/eso"
    msg = """{
                "soc": {"val": 0.0},
                "temp": {"val": 0.0},
                "wbatcons": {"val": 0},
                "ubat": {"val": 0.0},
                "ibat": {"val": 0.0},
                "relaystatus": {"val": "0"},
                "faultcode": {"val": "0"},
                "ts": {"val": "2021-03-03T01:03:55UTC"},
                "id": {"val": ""},
                "wbatprod": {"val": 0}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    assert er.async_is_registered("sensor.ferroamp_eso__battery_voltage") is False


async def test_setting_sso_sensor_values_via_mqtt_message(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/sso"
    msg = """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "0"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }"""
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_voltage")
    assert state.state == "653"
    assert state.attributes == {
        'device_class': 'voltage',
        'friendly_name': 'SSO 12345678 PV String Voltage',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_current")
    assert state.state == "5"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'SSO 12345678 PV String Current',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_power")
    assert state.state == "3151"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'SSO 12345678 PV String Power',
        'icon': 'mdi:solar-power',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_total_energy")
    assert state.state == "234.3"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'SSO 12345678 Total Energy',
        'icon': 'mdi:solar-power',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        0: 'No errors'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_relay_status")
    assert state.state == "closed"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Relay Status',
        'icon': '',
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pcb_temperature")
    assert state.state == "6"
    assert state.attributes == {
        'device_class': 'temperature',
        'friendly_name': 'SSO 12345678 PCB Temperature',
        'icon': 'mdi:thermometer',
        'state_class': 'measurement',
        'unit_of_measurement': '°C'
    }


async def test_trim_part_no_from_sso_id(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/sso"
    msg = """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "0"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "PS00990-A02-S12345678"}
            }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_voltage")
    assert state.state == "653"
    assert state.attributes == {
        'device_class': 'voltage',
        'friendly_name': 'SSO 12345678 PV String Voltage',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_current")
    assert state.state == "5"
    assert state.attributes == {
        'device_class': 'current',
        'friendly_name': 'SSO 12345678 PV String Current',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'A'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pv_string_power")
    assert state.state == "3151"
    assert state.attributes == {
        'device_class': 'power',
        'friendly_name': 'SSO 12345678 PV String Power',
        'icon': 'mdi:solar-power',
        'state_class': 'measurement',
        'unit_of_measurement': 'W'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_total_energy")
    assert state.state == "234.3"
    assert state.attributes == {
        'device_class': 'energy',
        'friendly_name': 'SSO 12345678 Total Energy',
        'icon': 'mdi:solar-power',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        0: 'No errors'
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_relay_status")
    assert state.state == "closed"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Relay Status',
        'icon': '',
    }

    state = hass.states.get("sensor.ferroamp_sso_12345678_pcb_temperature")
    assert state.state == "6"
    assert state.attributes == {
        'device_class': 'temperature',
        'friendly_name': 'SSO 12345678 PCB Temperature',
        'icon': 'mdi:thermometer',
        'state_class': 'measurement',
        'unit_of_measurement': '°C'
    }

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_sso_12345678_pv_string_voltage")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_sso_12345678"][entity.unique_id]
    assert isinstance(sensor, VoltageFerroampSensor)
    assert sensor.device_info.get("model") == "PS00990-A02"


async def test_migrate_old_sso_entities(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_sso_PS00990-A02-S12345678-upv', config_entry=config_entry)

    topic = "extapi/data/sso"
    msg = """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "0"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "PS00990-A02-S12345678"}
            }"""

    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get(entity.entity_id)
    assert state.state == "653"
    assert state.attributes == {
        'device_class': 'voltage',
        'friendly_name': 'SSO 12345678 PV String Voltage',
        'icon': 'mdi:current-dc',
        'state_class': 'measurement',
        'unit_of_measurement': 'V'
    }


async def test_sso_fault_codes(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/sso"
    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "0"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        0: 'No errors'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "4"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "4"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        3: 'Error, PV ground fault'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "8"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "8"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        4: 'Error, internal voltage unbalance'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "10"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "10"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        5: 'Warning, PV undervoltage, not possible to sustain MPPT operation'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "20"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "20"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        6: 'Warning, DC grid voltage too high, SSO will not connect to DC grid'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "40"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "40"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        7: 'Warning, Limiting current due to internal temperature'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "80"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "80"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        8: 'Error, Internal power electronics fault'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "100"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "100"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        9: 'Error, Internal relay test circuit has detected a fault'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "200"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "200"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        10: 'Error, Memory error, configuration parameters can not be read'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "400"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "400"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        11: 'Warning, SSO is limiting power, either because of internal temperature or DC grid voltage level'
    }

    async_fire_mqtt_message(hass, topic, """{
                "relaystatus": {"val": "0"},
                "temp": {"val": "6.482"},
                "wpv": {"val": "843516404273"},
                "ts": {"val": "2021-03-08T08:22:42UTC"},
                "udc": {"val": "769.872"},
                "faultcode": {"val": "0"},
                "ipv": {"val": "4.826"},
                "upv": {"val": "653.012"},
                "id": {"val": "12345678"}
            }""")
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_sso_12345678_faultcode")
    assert state.state == "0"
    assert state.attributes == {
        'friendly_name': 'SSO 12345678 Faultcode',
        'icon': 'mdi:traffic-light',
        0: 'No errors'
    }


async def test_restore_state(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_esm_1_state_of_charge", "11")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/esm"
    msg = '{"id":{"val":"1"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_1_state_of_charge")
    assert state.state == "11"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESM 1 State of Charge',
        'icon': 'mdi:battery-10',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }


async def test_restore_state_unknown(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_esm_1_state_of_charge", "unknown")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/esm"
    msg = '{"id":{"val":"1"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_esm_1_state_of_charge")
    assert state.state == "unknown"
    assert state.attributes == {
        'device_class': 'battery',
        'friendly_name': 'ESM 1 State of Charge',
        'icon': 'mdi:battery-low',
        'state_class': 'measurement',
        'unit_of_measurement': '%'
    }


async def test_update_options(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    msg = '{"id":{"val":"1"},"wpv":{"val": "4422089590383"}}'
    async_fire_mqtt_message(hass, "extapi/data/ehub", msg)
    async_fire_mqtt_message(hass, "extapi/data/esm", msg)
    async_fire_mqtt_message(hass, "extapi/data/eso", msg)
    async_fire_mqtt_message(hass, "extapi/data/sso", msg)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_INTERVAL: 20,
            CONF_PRECISION_BATTERY: 1,
            CONF_PRECISION_CURRENT: 2,
            CONF_PRECISION_ENERGY: 0,
            CONF_PRECISION_TEMPERATURE: 3,
            CONF_PRECISION_VOLTAGE: 4,
        }
    )
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_esm_1_state_of_charge")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_esm_1"][entity.unique_id]
    assert isinstance(sensor, BatteryFerroampSensor)
    assert sensor._interval == 20
    assert sensor._precision == 1

    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert isinstance(sensor, EnergyFerroampSensor)
    assert sensor._interval == 20
    assert sensor._precision == 0

    entity = er.async_get("sensor.ferroamp_eso_1_pcb_temperature")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_eso_1"][entity.unique_id]
    assert isinstance(sensor, TemperatureFerroampSensor)
    assert sensor._interval == 20
    assert sensor._precision == 3

    entity = er.async_get("sensor.ferroamp_sso_1_pv_string_voltage")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_sso_1"][entity.unique_id]
    assert isinstance(sensor, VoltageFerroampSensor)
    assert sensor._interval == 20
    assert sensor._precision == 4

    async_fire_mqtt_message(hass, "extapi/data/ehub", msg)
    async_fire_mqtt_message(hass, "extapi/data/esm", msg)
    async_fire_mqtt_message(hass, "extapi/data/eso", msg)
    async_fire_mqtt_message(hass, "extapi/data/sso", msg)
    await hass.async_block_till_done()

    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == 1228.4


async def test_base_class_update_state_from_events():
    sensor = KeyedFerroampSensor("test", "prefix", "key", "", "", "", "", 20, "a")
    with pytest.raises(Exception):
        sensor.update_state_from_events([{}])


async def test_control_command(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    msg = """{
                "transId": "abc-123",
                "cmd": {"name": "charge", "arg": "5000"}
            }"""
    async_fire_mqtt_message(hass, "extapi/control/request", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_control_status")
    assert state.state == "charge (5000)"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Control Status',
        'icon': 'mdi:cog-transfer-outline',
        'transId': 'abc-123',
        'status': None,
        'message': None
    }

    async_fire_mqtt_message(hass, "extapi/control/request", msg)
    await hass.async_block_till_done()

    msg = """{
                "transId": "xxx-123",
                "status": "ack",
                "msg": "some message"
            }"""
    async_fire_mqtt_message(hass, "extapi/control/response", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_control_status")
    assert state.state == "charge (5000)"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Control Status',
        'icon': 'mdi:cog-transfer-outline',
        'transId': 'abc-123',
        'status': None,
        'message': None
    }

    msg = """{
                "transId": "abc-123",
                "status": "ack",
                "msg": "some message"
            }"""
    async_fire_mqtt_message(hass, "extapi/control/response", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_control_status")
    assert state.state == "charge (5000)"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Control Status',
        'icon': 'mdi:cog-transfer-outline',
        'transId': 'abc-123',
        'status': "ack",
        'message': "some message"
    }

    msg = """{
                "transId": "abc-123",
                "status": "nack",
                "msg": "other message"
            }"""
    async_fire_mqtt_message(hass, "extapi/control/result", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_control_status")
    assert state.state == "charge (5000)"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Control Status',
        'icon': 'mdi:cog-transfer-outline',
        'transId': 'abc-123',
        'status': "nack",
        'message': "other message"
    }


async def test_control_command_restore_state(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.control_status", "auto")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    msg = """{
                "transId": "abc-123",
                "cmd": {"name": "charge", "arg": "5000"}
            }"""
    async_fire_mqtt_message(hass, "extapi/control/request", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_control_status")
    assert state.state == "charge (5000)"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Control Status',
        'icon': 'mdi:cog-transfer-outline',
        'transId': 'abc-123',
        'status': None,
        'message': None
    }


async def test_always_increasing(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_total_solar_energy", "1348.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    msg = '{"id":{"val":"1"},"wpv":{"val": "4422089590383"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == "1348.5"

async def test_always_increasing_zerovalues(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_total_solar_energy", "1348.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "4422089590383"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert float(sensor.state) == pytest.approx(1348.5)

    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "4856400000000"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "0"}}')
    async_fire_mqtt_message(hass, topic, '{"id":{"val":"1"},"wpv":{"val": "4856400000000"}}')
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert float(sensor.state) == pytest.approx(1349.0)


async def test_always_increasing_unknown_value(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_total_solar_energy", "unknown")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    msg = '{"id":{"val":"1"},"wpv":{"val": "4422089590383"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == 1228.4


async def test_always_increasing_counter_reset(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_total_solar_energy", "1348.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    # 100 kWh
    msg = '{"id":{"val":"1"},"wpv":{"val": "360000000000"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_total_solar_energy")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == 100.0


async def test_3phase_always_increasing(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_external_energy_produced", "662.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_external_energy_produced")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == "662.5"

async def test_3phase_always_increasing_zero_values(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_external_energy_produced", "662.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"}}'
    async_fire_mqtt_message(hass, topic, msg)
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "0", "L3": "0", "L1": "0"}}'
    async_fire_mqtt_message(hass, topic, msg)
    async_fire_mqtt_message(hass, topic, msg)
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_external_energy_produced")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert float(sensor.state) == pytest.approx(662.5)

    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"}}'
    async_fire_mqtt_message(hass, topic, msg)
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "0", "L3": "0", "L1": "0"}}'
    async_fire_mqtt_message(hass, topic, msg)
    async_fire_mqtt_message(hass, topic, msg)
    async_fire_mqtt_message(hass, topic, msg)
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "1119056851556", "L3": "604564554552", "L1": "662116344893"}}'
    async_fire_mqtt_message(hass, topic, msg)
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "0", "L3": "0", "L1": "0"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_external_energy_produced")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert float(sensor.state) == pytest.approx(662.7)

async def test_3phase_always_increasing_unknown_value(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_external_energy_produced", "unknown")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "1118056851556", "L3": "604554554552", "L1": "662115344893"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_external_energy_produced")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == 662.4


async def test_3phase_always_increasing_counter_reset(hass, mqtt_mock):
    mock_restore_cache(
        hass,
        [
            State("sensor.ferroamp_external_energy_produced", "662.5")
        ],
    )

    hass.state = CoreState.starting

    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    topic = "extapi/data/ehub"
    # 10 kWh on each phase
    msg = '{"id":{"val":"1"},"wextprodq": {"L2": "36000000000", "L3": "36000000000", "L1": "36000000000"}}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    er = entity_registry.async_get(hass)
    entity = er.async_get("sensor.ferroamp_external_energy_produced")
    assert entity is not None
    sensor = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]["ferroamp_ehub"][entity.unique_id]
    assert sensor.state == 30.0


async def test_average_calculation(hass, mqtt_mock):
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Ferroamp",
            CONF_PREFIX: "extapi"
        },
        options={
            CONF_INTERVAL: 1,
            CONF_PRECISION_BATTERY: 0,
            CONF_PRECISION_CURRENT: 0,
            CONF_PRECISION_ENERGY: 0,
            CONF_PRECISION_FREQUENCY: 0,
            CONF_PRECISION_TEMPERATURE: 0,
            CONF_PRECISION_VOLTAGE: 0,
        },
        version=1,
        unique_id="ferroamp",
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    er = entity_registry.async_get(hass)
    er.async_get_or_create(
        'sensor', DOMAIN, 'ferroamp_ehub-wextprodq', config_entry=config_entry,
        suggested_object_id="ferroamp_external_energy_produced")

    await hass.async_block_till_done()

    topic = "extapi/data/ehub"

    def msg(l1, l2, l3) -> str:
        return f"""{{"wextprodq": {{"L1": "{l1}", "L2": "{l2}", "L3": "{l3}"}}}}"""

    async_fire_mqtt_message(hass, topic, msg(662115344893, 1118056851556, 604554554552))
    async_fire_mqtt_message(hass, topic, "{}")
    async_fire_mqtt_message(hass, topic, msg(662115344893, 1118056851556, 604554554552))
    async_fire_mqtt_message(hass, topic, "{}")
    async_fire_mqtt_message(hass, topic, "{}")
    async_fire_mqtt_message(hass, topic, msg(662115344893, 1118056851556, 604554554552))
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_external_energy_produced")
    assert state.state == "662"
    assert state.attributes == {
        'L1': 183.92,
        'L2': 310.57,
        'L3': 167.93,
        'device_class': 'energy',
        'friendly_name': 'EnergyHub External Energy Produced',
        'icon': 'mdi:power-plug',
        'state_class': 'total_increasing',
        'unit_of_measurement': 'kWh'
    }


@patch('uuid.uuid1', mock_uuid)
async def test_extapi_version_request(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    topic = "extapi/data/ehub"
    msg = '{}'
    async_fire_mqtt_message(hass, topic, msg)
    await hass.async_block_till_done()

    mqtt_mock.async_publish.assert_called_once_with(
        "extapi/control/request",
        '{"transId": "00000000-0000-0000-0000-000000000001", "cmd": {"name": "extapiversion"}}',
        0,
        False
    )


async def test_extapi_version_response(hass, mqtt_mock):
    config_entry = create_config()
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    msg = """{
                "transId": "xxx-123",
                "status": "ack",
                "msg": "version: 1.2.3"
            }"""
    async_fire_mqtt_message(hass, "extapi/control/response", msg)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.ferroamp_extapi_version")
    assert state.state == "1.2.3"
    assert state.attributes == {
        'friendly_name': 'EnergyHub Extapi Version',
        'icon': 'mdi:counter'
    }
