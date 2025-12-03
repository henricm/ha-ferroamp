"""Platform for Ferroamp sensors integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import logging
from typing import Any
import uuid

from homeassistant import config_entries, core
from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PREFIX,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    async_get as async_get_entity_reg,
)
from homeassistant.helpers.icon import icon_for_battery_level
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_INTERVAL,
    DATA_DEVICES,
    DATA_LISTENERS,
    DOMAIN,
    EHUB,
    EHUB_NAME,
    FAULT_CODES_ESO,
    FAULT_CODES_SSO,
    MANUFACTURER,
    REGEX_ESM_ID,
    REGEX_SSO_ID,
    TOPIC_CONTROL_REQUEST,
    TOPIC_CONTROL_RESPONSE,
    TOPIC_CONTROL_RESULT,
    TOPIC_EHUB,
    TOPIC_ESM,
    TOPIC_ESO,
    TOPIC_SSO,
)
from .mqtt_parser import (
    CommandParser,
    MqttEvent,
    MqttMessageParser,
    PhaseValues,
    average_dc_link_values,
    average_float_values,
    average_int_values,
    average_phase_values,
    average_single_phase_values,
    convert_to_kwh,
    last_string_value,
)

_LOGGER = logging.getLogger(__name__)

# Type alias for sensor storage
SensorStore = dict[str, "FerroampSensor"]


class SensorType(Enum):
    """Enumeration of sensor types for data-driven sensor creation."""

    FLOAT = "float"
    INT = "int"
    STRING = "string"
    VOLTAGE = "voltage"
    CURRENT = "current"
    POWER = "power"
    ENERGY = "energy"
    TEMPERATURE = "temperature"
    BATTERY = "battery"
    PERCENTAGE = "percentage"
    THREE_PHASE = "three_phase"
    THREE_PHASE_POWER = "three_phase_power"
    THREE_PHASE_ENERGY = "three_phase_energy"
    THREE_PHASE_MIN = "three_phase_min"
    SINGLE_PHASE = "single_phase"
    SINGLE_PHASE_POWER = "single_phase_power"
    SINGLE_PHASE_ENERGY = "single_phase_energy"
    DC_LINK = "dc_link"


@dataclass
class EhubSensorConfig:
    """Configuration for an EnergyHub sensor."""

    name: str
    key: str
    sensor_type: SensorType
    icon: str
    unit: str | None = None
    phase: str | None = None
    state_class: SensorStateClass | None = None
    check_presence: bool = False


# EnergyHub sensor definitions - data-driven approach
EHUB_SENSOR_CONFIGS: list[EhubSensorConfig] = [
    # Frequency
    EhubSensorConfig(
        "Estimated Grid Frequency",
        "gridfreq",
        SensorType.FLOAT,
        "mdi:sine-wave",
        UnitOfFrequency.HERTZ,
    ),
    # External Voltage (3-phase + individual)
    EhubSensorConfig(
        "External Voltage",
        "ul",
        SensorType.THREE_PHASE,
        "mdi:current-ac",
        UnitOfElectricPotential.VOLT,
    ),
    EhubSensorConfig(
        "External Voltage L1",
        "ul",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricPotential.VOLT,
        "L1",
    ),
    EhubSensorConfig(
        "External Voltage L2",
        "ul",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricPotential.VOLT,
        "L2",
    ),
    EhubSensorConfig(
        "External Voltage L3",
        "ul",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricPotential.VOLT,
        "L3",
    ),
    # Inverter RMS Current
    EhubSensorConfig(
        "Inverter RMS Current",
        "il",
        SensorType.THREE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "Inverter RMS Current L1",
        "il",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "Inverter RMS Current L2",
        "il",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "Inverter RMS Current L3",
        "il",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # Inverter Reactive Current
    EhubSensorConfig(
        "Inverter Reactive Current",
        "ild",
        SensorType.THREE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "Inverter Reactive Current L1",
        "ild",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "Inverter Reactive Current L2",
        "ild",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "Inverter Reactive Current L3",
        "ild",
        SensorType.SINGLE_PHASE,
        "mdi:current-dc",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # Grid Current
    EhubSensorConfig(
        "Grid Current",
        "iext",
        SensorType.THREE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "Grid Current L1",
        "iext",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "Grid Current L2",
        "iext",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "Grid Current L3",
        "iext",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # Grid Reactive Current
    EhubSensorConfig(
        "Grid Reactive Current",
        "iextd",
        SensorType.THREE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "Grid Reactive Current L1",
        "iextd",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "Grid Reactive Current L2",
        "iextd",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "Grid Reactive Current L3",
        "iextd",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # External Active Current
    EhubSensorConfig(
        "External Active Current",
        "iextq",
        SensorType.THREE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "External Active Current L1",
        "iextq",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "External Active Current L2",
        "iextq",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "External Active Current L3",
        "iextq",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # Adaptive Current Equalization
    EhubSensorConfig(
        "Adaptive Current Equalization",
        "iace",
        SensorType.THREE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
    ),
    EhubSensorConfig(
        "Adaptive Current Equalization L1",
        "iace",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L1",
    ),
    EhubSensorConfig(
        "Adaptive Current Equalization L2",
        "iace",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L2",
    ),
    EhubSensorConfig(
        "Adaptive Current Equalization L3",
        "iace",
        SensorType.SINGLE_PHASE,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        "L3",
    ),
    # Grid Power
    EhubSensorConfig(
        "Grid Power", "pext", SensorType.THREE_PHASE_POWER, "mdi:transmission-tower"
    ),
    EhubSensorConfig(
        "Grid Power L1",
        "pext",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L1",
    ),
    EhubSensorConfig(
        "Grid Power L2",
        "pext",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L2",
    ),
    EhubSensorConfig(
        "Grid Power L3",
        "pext",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L3",
    ),
    # Grid Power Reactive
    EhubSensorConfig(
        "Grid Power Reactive",
        "pextreactive",
        SensorType.THREE_PHASE_POWER,
        "mdi:transmission-tower",
    ),
    EhubSensorConfig(
        "Grid Power Reactive L1",
        "pextreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L1",
    ),
    EhubSensorConfig(
        "Grid Power Reactive L2",
        "pextreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L2",
    ),
    EhubSensorConfig(
        "Grid Power Reactive L3",
        "pextreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:transmission-tower",
        phase="L3",
    ),
    # Inverter Power Active
    EhubSensorConfig(
        "Inverter Power, Active",
        "pinv",
        SensorType.THREE_PHASE_POWER,
        "mdi:solar-power",
    ),
    EhubSensorConfig(
        "Inverter Power, Active L1",
        "pinv",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L1",
    ),
    EhubSensorConfig(
        "Inverter Power, Active L2",
        "pinv",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L2",
    ),
    EhubSensorConfig(
        "Inverter Power, Active L3",
        "pinv",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L3",
    ),
    # Inverter Power Reactive
    EhubSensorConfig(
        "Inverter Power, Reactive",
        "pinvreactive",
        SensorType.THREE_PHASE_POWER,
        "mdi:solar-power",
    ),
    EhubSensorConfig(
        "Inverter Power, Reactive L1",
        "pinvreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L1",
    ),
    EhubSensorConfig(
        "Inverter Power, Reactive L2",
        "pinvreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L2",
    ),
    EhubSensorConfig(
        "Inverter Power, Reactive L3",
        "pinvreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:solar-power",
        phase="L3",
    ),
    # Consumption Power
    EhubSensorConfig(
        "Consumption Power", "pload", SensorType.THREE_PHASE_POWER, "mdi:power-plug"
    ),
    EhubSensorConfig(
        "Consumption Power L1",
        "pload",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Consumption Power L2",
        "pload",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Consumption Power L3",
        "pload",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L3",
    ),
    # Consumption Power Reactive
    EhubSensorConfig(
        "Consumption Power Reactive",
        "ploadreactive",
        SensorType.THREE_PHASE_POWER,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "Consumption Power Reactive L1",
        "ploadreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Consumption Power Reactive L2",
        "ploadreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Consumption Power Reactive L3",
        "ploadreactive",
        SensorType.SINGLE_PHASE_POWER,
        "mdi:power-plug",
        phase="L3",
    ),
    # External Energy Produced
    EhubSensorConfig(
        "External Energy Produced",
        "wextprodq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "External Energy Produced L1",
        "wextprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "External Energy Produced L2",
        "wextprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "External Energy Produced L3",
        "wextprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # External Energy Consumed
    EhubSensorConfig(
        "External Energy Consumed",
        "wextconsq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "External Energy Consumed L1",
        "wextconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "External Energy Consumed L2",
        "wextconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "External Energy Consumed L3",
        "wextconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # Inverter Energy Produced
    EhubSensorConfig(
        "Inverter Energy Produced",
        "winvprodq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "Inverter Energy Produced L1",
        "winvprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Inverter Energy Produced L2",
        "winvprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Inverter Energy Produced L3",
        "winvprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # Inverter Energy Consumed
    EhubSensorConfig(
        "Inverter Energy Consumed",
        "winvconsq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "Inverter Energy Consumed L1",
        "winvconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Inverter Energy Consumed L2",
        "winvconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Inverter Energy Consumed L3",
        "winvconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # Load Energy Produced
    EhubSensorConfig(
        "Load Energy Produced",
        "wloadprodq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "Load Energy Produced L1",
        "wloadprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Load Energy Produced L2",
        "wloadprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Load Energy Produced L3",
        "wloadprodq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # Load Energy Consumed
    EhubSensorConfig(
        "Load Energy Consumed",
        "wloadconsq",
        SensorType.THREE_PHASE_ENERGY,
        "mdi:power-plug",
    ),
    EhubSensorConfig(
        "Load Energy Consumed L1",
        "wloadconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L1",
    ),
    EhubSensorConfig(
        "Load Energy Consumed L2",
        "wloadconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L2",
    ),
    EhubSensorConfig(
        "Load Energy Consumed L3",
        "wloadconsq",
        SensorType.SINGLE_PHASE_ENERGY,
        "mdi:power-plug",
        phase="L3",
    ),
    # Solar and Battery
    EhubSensorConfig("Total Solar Energy", "wpv", SensorType.ENERGY, "mdi:solar-power"),
    EhubSensorConfig(
        "Battery Energy Produced",
        "wbatprod",
        SensorType.ENERGY,
        "mdi:battery-plus",
        check_presence=True,
    ),
    EhubSensorConfig(
        "Battery Energy Consumed",
        "wbatcons",
        SensorType.ENERGY,
        "mdi:battery-minus",
        check_presence=True,
    ),
    # System state
    EhubSensorConfig("System State", "state", SensorType.INT, "mdi:traffic-light", ""),
    EhubSensorConfig("DC Link Voltage", "udc", SensorType.DC_LINK, "mdi:current-ac"),
    EhubSensorConfig(
        "System State of Charge",
        "soc",
        SensorType.BATTERY,
        "mdi:battery",
        check_presence=True,
    ),
    EhubSensorConfig(
        "System State of Health",
        "soh",
        SensorType.PERCENTAGE,
        "mdi:battery-low",
        check_presence=True,
    ),
    EhubSensorConfig(
        "Apparent power", "sext", SensorType.INT, "mdi:transmission-tower", "VA"
    ),
    EhubSensorConfig(
        "Solar Power",
        "ppv",
        SensorType.POWER,
        "mdi:solar-power",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    EhubSensorConfig(
        "Battery Power",
        "pbat",
        SensorType.POWER,
        "mdi:battery",
        state_class=SensorStateClass.MEASUREMENT,
        check_presence=True,
    ),
    EhubSensorConfig(
        "Total Rated Capacity of All Batteries",
        "ratedcap",
        SensorType.INT,
        "mdi:battery",
        UnitOfEnergy.WATT_HOUR,
        check_presence=True,
    ),
    # Load balancing
    EhubSensorConfig(
        "Available Three Phase Active Current For Load Balancing",
        "iavblq_3p",
        SensorType.FLOAT,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        check_presence=True,
    ),
    EhubSensorConfig(
        "Available Active Current For Load Balancing",
        "iavblq",
        SensorType.THREE_PHASE_MIN,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        check_presence=True,
    ),
    EhubSensorConfig(
        "Available RMS Current For Load Balancing",
        "iavbl",
        SensorType.THREE_PHASE_MIN,
        "mdi:current-ac",
        UnitOfElectricCurrent.AMPERE,
        check_presence=True,
    ),
]


def create_sensor_from_config(
    config: EhubSensorConfig,
    slug: str,
    interval: int,
    config_id: str | None,
) -> FerroampSensor:
    """Create a sensor instance from configuration."""
    device_id = f"{slug}_{EHUB}"
    device_name = EHUB_NAME

    sensor_creators: dict[SensorType, Callable[[], FerroampSensor]] = {
        SensorType.FLOAT: lambda: FloatValFerroampSensor(
            config.name,
            slug,
            config.key,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
            state_class=config.state_class,
            check_presence=config.check_presence,
        ),
        SensorType.INT: lambda: IntValFerroampSensor(
            config.name,
            slug,
            config.key,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
            check_presence=config.check_presence,
        ),
        SensorType.STRING: lambda: StringValFerroampSensor(
            config.name,
            slug,
            config.key,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.VOLTAGE: lambda: VoltageFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.CURRENT: lambda: CurrentFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.POWER: lambda: PowerFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
            state_class=config.state_class,
            check_presence=config.check_presence,
        ),
        SensorType.ENERGY: lambda: EnergyFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
            check_presence=config.check_presence,
        ),
        SensorType.TEMPERATURE: lambda: TemperatureFerroampSensor(
            config.name,
            slug,
            config.key,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.BATTERY: lambda: BatteryFerroampSensor(
            config.name,
            slug,
            config.key,
            device_id,
            device_name,
            interval,
            config_id,
            check_presence=config.check_presence,
        ),
        SensorType.PERCENTAGE: lambda: PercentageFerroampSensor(
            config.name,
            slug,
            config.key,
            device_id,
            device_name,
            interval,
            config_id,
            check_presence=config.check_presence,
        ),
        SensorType.THREE_PHASE: lambda: ThreePhaseFerroampSensor(
            config.name,
            slug,
            config.key,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.THREE_PHASE_POWER: lambda: ThreePhasePowerFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.THREE_PHASE_ENERGY: lambda: ThreePhaseEnergyFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.THREE_PHASE_MIN: lambda: ThreePhaseMinFerroampSensor(
            config.name,
            slug,
            config.key,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
            check_presence=config.check_presence,
        ),
        SensorType.SINGLE_PHASE: lambda: SinglePhaseFerroampSensor(
            config.name,
            slug,
            config.key,
            config.phase,
            config.unit,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.SINGLE_PHASE_POWER: lambda: SinglePhasePowerFerroampSensor(
            config.name,
            slug,
            config.key,
            config.phase,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.SINGLE_PHASE_ENERGY: lambda: SinglePhaseEnergyFerroampSensor(
            config.name,
            slug,
            config.key,
            config.phase,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
        SensorType.DC_LINK: lambda: DcLinkFerroampSensor(
            config.name,
            slug,
            config.key,
            config.icon,
            device_id,
            device_name,
            interval,
            config_id,
        ),
    }

    creator = sensor_creators.get(config.sensor_type)
    if creator is None:
        raise ValueError(f"Unknown sensor type: {config.sensor_type}")
    return creator()


def ehub_sensors(
    slug: str,
    interval: int,
    config_id: str | None,
) -> list[FerroampSensor]:
    """Create all EnergyHub sensors from configuration."""
    return [
        create_sensor_from_config(config, slug, interval, config_id)
        for config in EHUB_SENSOR_CONFIGS
    ]


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up sensors from a config entry created in the integrations UI."""
    hass.data[DOMAIN].setdefault(DATA_DEVICES, {})
    hass.data[DOMAIN].setdefault(DATA_LISTENERS, {})
    hass.data[DOMAIN][DATA_DEVICES].setdefault(config_entry.unique_id, {})
    hass.data[DOMAIN][DATA_LISTENERS].setdefault(config_entry.unique_id, [])
    listeners: list[Callable[[], None]] = hass.data[DOMAIN][DATA_LISTENERS].get(
        config_entry.unique_id
    )
    config: dict[str, SensorStore] = hass.data[DOMAIN][DATA_DEVICES][
        config_entry.unique_id
    ]
    _LOGGER.debug(
        "Setting up ferroamp sensors for %(prefix)s",
        {"prefix": config_entry.data[CONF_PREFIX]},
    )
    config_id = config_entry.unique_id
    name = config_entry.data[CONF_NAME]
    slug = slugify(name)

    interval = get_option(config_entry, CONF_INTERVAL, 30)

    listeners.append(config_entry.add_update_listener(options_update_listener))

    entity_registry = async_get_entity_reg(hass)

    ehub = ehub_sensors(slug, interval, config_id)
    eso_sensors: dict[str, list[FerroampSensor]] = {}
    esm_sensors: dict[str, list[FerroampSensor]] = {}
    sso_sensors: dict[str, list[FerroampSensor]] = {}
    generic_sensors: dict[str, FerroampSensor] = {}

    def get_store(store_name: str) -> tuple[SensorStore, bool]:
        store = config.get(store_name)
        new = False
        if store is None:
            store = config[store_name] = {}
            new = True
        return store, new

    def register_sensor(
        sensor: FerroampSensor, event: MqttEvent | None, store: SensorStore
    ) -> None:
        if sensor.unique_id not in store:
            if not sensor.check_presence or sensor.present(event):
                store[sensor.unique_id] = sensor
                _LOGGER.debug(
                    "Registering new sensor %(unique_id)s => %(event)s",
                    {"unique_id": sensor.unique_id, "event": event},
                )
                async_add_entities((sensor,), True)

    def update_sensor_from_event(
        event: MqttEvent, sensors: list[FerroampSensor], store: SensorStore
    ) -> None:
        _LOGGER.debug("Event received %s", event)
        for sensor in sensors:
            register_sensor(sensor, event, store)
            sensor.hass = hass
            sensor.add_event(event)

    @callback
    def ehub_event_received(msg: mqtt.ReceiveMessage) -> None:
        event = MqttMessageParser.parse_message(msg)
        store, _ = get_store(f"{slug}_{EHUB}")
        update_sensor_from_event(event, ehub, store)

    @callback
    def sso_event_received(msg: mqtt.ReceiveMessage) -> None:
        event = MqttMessageParser.parse_message(msg)
        sso_id = MqttMessageParser.get_id(event)
        model = None
        match = REGEX_SSO_ID.match(sso_id)
        if match is not None and match.group(2) is not None:
            migrate_entities(
                sso_id,
                match.group(3),
                ["upv", "ipv", "upv-ipv", "wpv", "faultcode", "relaystatus", "temp"],
                slug,
                entity_registry,
                lambda s, i: build_sso_device_id(s, i),
            )
            sso_id = match.group(3)
            model = match.group(2)
        device_id = build_sso_device_id(slug, sso_id)
        device_name = f"SSO {sso_id}"
        store, new = get_store(device_id)
        sensors = sso_sensors.get(sso_id)
        if new:
            sensors = sso_sensors[sso_id] = [
                VoltageFerroampSensor(
                    "PV String Voltage",
                    device_id,
                    "upv",
                    "mdi:current-dc",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                CurrentFerroampSensor(
                    "PV String Current",
                    device_id,
                    "ipv",
                    "mdi:current-dc",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                CalculatedPowerFerroampSensor(
                    "PV String Power",
                    device_id,
                    "upv",
                    "ipv",
                    "mdi:solar-power",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                EnergyFerroampSensor(
                    "Total Energy",
                    device_id,
                    "wpv",
                    "mdi:solar-power",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                FaultcodeFerroampSensor(
                    "Faultcode",
                    device_id,
                    "faultcode",
                    device_id,
                    device_name,
                    interval,
                    FAULT_CODES_SSO,
                    config_id,
                    model=model,
                ),
                RelayStatusFerroampSensor(
                    "Relay Status",
                    device_id,
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                TemperatureFerroampSensor(
                    "PCB Temperature",
                    device_id,
                    "temp",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
            ]

        if sensors is not None:
            update_sensor_from_event(event, sensors, store)

    @callback
    def eso_event_received(msg: mqtt.ReceiveMessage) -> None:
        event = MqttMessageParser.parse_message(msg)
        eso_id = MqttMessageParser.get_id(event)
        if not eso_id:
            return
        device_id = f"{slug}_eso_{eso_id}"
        device_name = f"ESO {eso_id}"
        store, new = get_store(device_id)
        sensors = eso_sensors.get(eso_id)
        if new:
            sensors = eso_sensors[eso_id] = [
                VoltageFerroampSensor(
                    "Battery Voltage",
                    device_id,
                    "ubat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                CurrentFerroampSensor(
                    "Battery Current",
                    device_id,
                    "ibat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                CalculatedPowerFerroampSensor(
                    "Battery Power",
                    device_id,
                    "ubat",
                    "ibat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                EnergyFerroampSensor(
                    "Total Energy Produced",
                    device_id,
                    "wbatprod",
                    "mdi:battery-plus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                EnergyFerroampSensor(
                    "Total Energy Consumed",
                    device_id,
                    "wbatcons",
                    "mdi:battery-minus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                BatteryFerroampSensor(
                    "State of Charge",
                    device_id,
                    "soc",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                FaultcodeFerroampSensor(
                    "Faultcode",
                    device_id,
                    "faultcode",
                    device_id,
                    device_name,
                    interval,
                    FAULT_CODES_ESO,
                    config_id,
                ),
                RelayStatusFerroampSensor(
                    "Relay Status",
                    device_id,
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                TemperatureFerroampSensor(
                    "PCB Temperature",
                    device_id,
                    "temp",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
            ]

        if sensors is not None:
            update_sensor_from_event(event, sensors, store)

    @callback
    def esm_event_received(msg: mqtt.ReceiveMessage) -> None:
        event = MqttMessageParser.parse_message(msg)
        esm_id = MqttMessageParser.get_id(event)
        model = None
        device_id = f"{slug}_esm_{esm_id}"
        device_name = f"ESM {esm_id}"
        match = REGEX_ESM_ID.match(esm_id)
        if (
            match is not None
            and match.group(2) is not None
            and match.group(1) is not None
        ):
            migrate_entities(
                esm_id,
                match.group(2),
                ["status", "soh", "soc", "ratedCapacity", "ratedPower"],
                slug,
                entity_registry,
                lambda s, i: build_esm_device_id(s, i),
            )
            esm_id = match.group(2)
            model = match.group(1)
            device_id = f"{slug}_esm_{esm_id}"
            device_name = f"ESM {esm_id}"
        store, new = get_store(device_id)
        sensors = esm_sensors.get(esm_id)
        if new:
            sensors = esm_sensors[esm_id] = [
                StringValFerroampSensor(
                    "Status",
                    device_id,
                    "status",
                    "",
                    "mdi:traffic-light",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                PercentageFerroampSensor(
                    "State of Health",
                    device_id,
                    "soh",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                BatteryFerroampSensor(
                    "State of Charge",
                    device_id,
                    "soc",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                IntValFerroampSensor(
                    "Rated Capacity",
                    device_id,
                    "ratedCapacity",
                    UnitOfEnergy.WATT_HOUR,
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
                PowerFerroampSensor(
                    "Rated Power",
                    device_id,
                    "ratedPower",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model,
                ),
            ]

        if sensors is not None:
            update_sensor_from_event(event, sensors, store)

    def get_generic_sensor(
        store: SensorStore,
        sensor_type: str,
        sensor_creator: Callable[[], FerroampSensor],
    ) -> FerroampSensor:
        sensor = generic_sensors.get(sensor_type)
        if sensor is None:
            sensor = sensor_creator()
            generic_sensors[sensor_type] = sensor
            register_sensor(sensor, None, store)
            sensor.hass = hass
        return sensor

    def get_cmd_sensor(store: SensorStore) -> CommandFerroampSensor:
        return get_generic_sensor(
            store,
            "cmd",
            lambda: CommandFerroampSensor(
                "Control Status", slug, f"{slug}_{EHUB}", EHUB_NAME, config_id
            ),
        )

    def get_version_sensor(store: SensorStore) -> VersionFerroampSensor:
        return get_generic_sensor(
            store,
            "version",
            lambda: VersionFerroampSensor(
                "Extapi Version", slug, f"{slug}_{EHUB}", EHUB_NAME, config_id
            ),
        )

    @callback
    def ehub_request_received(msg: mqtt.ReceiveMessage) -> None:
        command = MqttMessageParser.parse_message(msg)
        store, _ = get_store(f"{slug}_{EHUB}")
        sensor = get_cmd_sensor(store)
        trans_id, cmd_name, arg = CommandParser.parse_request(command)
        sensor.add_request(trans_id, cmd_name, arg)

    @callback
    def ehub_response_received(msg: mqtt.ReceiveMessage) -> None:
        response = MqttMessageParser.parse_message(msg)
        trans_id, status, message = CommandParser.parse_response(response)
        store, _ = get_store(f"{slug}_{EHUB}")
        if CommandParser.is_version_response(message):
            sensor = get_version_sensor(store)
            sensor.set_version(CommandParser.extract_version(message))
        else:
            sensor = get_cmd_sensor(store)
            sensor.add_response(trans_id, status, message)

    store, _ = get_store(f"{slug}_{EHUB}")
    get_version_sensor(store)
    get_cmd_sensor(store)

    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_EHUB}",
            ehub_event_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_SSO}",
            sso_event_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_ESO}",
            eso_event_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_ESM}",
            esm_event_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_REQUEST}",
            ehub_request_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_RESPONSE}",
            ehub_response_received,
            0,
        )
    )
    listeners.append(
        await mqtt.async_subscribe(
            hass,
            f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_RESULT}",
            ehub_response_received,
            0,
        )
    )

    payload = {"transId": str(uuid.uuid1()), "cmd": {"name": "extapiversion"}}
    await mqtt.async_publish(
        hass,
        f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_REQUEST}",
        json.dumps(payload),
    )

    return True


def get_option(config_entry: config_entries.ConfigEntry, key: str, default: int) -> int:
    """Get option value from config entry with default fallback."""
    value = config_entry.options.get(key)
    if value is None:
        value = default
    return value


def build_sso_device_id(slug: str, sso_id: str) -> str:
    """Build device ID for SSO device."""
    return f"{slug}_sso_{sso_id}"


def build_esm_device_id(slug: str, esm_id: str) -> str:
    """Build device ID for ESM device."""
    return f"{slug}_esm_{esm_id}"


def migrate_entities(
    old_id: str,
    new_id: str,
    keys: list[str],
    slug: str,
    entity_registry: EntityRegistry,
    build_device_id: Callable[[str, str], str],
) -> None:
    """Migrate entities from old ID to new ID."""
    for key in keys:
        old_entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{build_device_id(slug, old_id)}-{key}"
        )
        if old_entity_id is not None:
            entity_registry.async_update_entity(
                old_entity_id, new_unique_id=f"{build_device_id(slug, new_id)}-{key}"
            )


async def options_update_listener(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Handle options update."""
    config: dict[str, SensorStore] = hass.data[DOMAIN][DATA_DEVICES][entry.unique_id]
    for device in config.values():
        for sensor in device.values():
            sensor.handle_options_update(entry.options)


def isfloat(value: Any) -> bool:
    """Check if value can be converted to float."""
    try:
        float(value)
        return True
    except ValueError:
        return False


class FerroampSensor(SensorEntity, RestoreEntity):
    """Representation of a Ferroamp Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        unit: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_has_entity_name = True
        self._attr_unit_of_measurement = unit
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=kwargs.get("model"),
        )
        self._attr_should_poll = False
        if unit == UnitOfEnergy.KILO_WATT_HOUR:
            self._attr_device_class = SensorDeviceClass.ENERGY
        elif unit == UnitOfPower.WATT:
            self._attr_device_class = SensorDeviceClass.POWER
        elif unit == UnitOfElectricPotential.VOLT:
            self._attr_device_class = SensorDeviceClass.VOLTAGE
        elif unit == UnitOfElectricCurrent.AMPERE:
            self._attr_device_class = SensorDeviceClass.CURRENT
        elif unit == UnitOfTemperature.CELSIUS:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._interval = interval
        entity_id = slugify(name)
        self.entity_id = f"sensor.{entity_prefix}_{entity_id}"
        self.device_id = device_id
        self.config_id = config_id
        self._attr_state_class = kwargs.get("state_class")
        self._added = False
        self.check_presence: bool = kwargs.get("check_presence", False)

    def present(self, event: MqttEvent | None) -> bool:
        """Check if sensor data is present in event."""
        return True

    def add_event(self, event: MqttEvent) -> None:
        """Add MQTT event data - override in subclasses."""
        pass

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state and state.state != "unknown":
            self._attr_native_value = state.state
        self.hass.data[DOMAIN][DATA_DEVICES][self.config_id][self.device_id][
            self.unique_id
        ] = self
        self._added = True

    def handle_options_update(self, options: dict[str, Any]) -> None:
        """Handle options update."""
        self._interval = options.get(CONF_INTERVAL, self._interval)


class KeyedFerroampSensor(FerroampSensor):
    """Ferroamp Sensor using a single key to extract state from MQTT messages."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        unit: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            unit,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._state_key = key
        self._attr_unique_id = f"{self.device_id}-{self._state_key}"
        self.updated = datetime.min
        self.events: list[MqttEvent] = []
        self.check_presence = kwargs.get("check_presence", False)

    def present(self, event: MqttEvent | None) -> bool:
        """Check if sensor data is present in event."""
        if event is None:
            return False
        return MqttMessageParser.key_present(event, self._state_key)

    def get_value(self, event: MqttEvent) -> dict[str, Any] | None:
        """Get raw value from event."""
        return MqttMessageParser.get_value(event, self._state_key)

    def get_float_value(self, event: MqttEvent) -> float:
        """Get float value from event."""
        val = MqttMessageParser.get_float(event, self._state_key)
        if val is None:
            return 0
        return val

    def add_event(self, event: MqttEvent) -> None:
        """Add MQTT event to processing queue."""
        if not self.check_presence or self.present(event):
            self.events.append(event)
        now = datetime.now()
        delta = (now - self.updated).total_seconds()
        if delta > self._interval and self._added:
            self.process_events(now)

    def process_events(self, now: datetime) -> None:
        """Process accumulated events and update state."""
        temp = self.events
        self.events = []
        self.updated = now
        if len(temp) != 0:
            if self.update_state_from_events(temp):
                self.async_write_ha_state()

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events - must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement update_state_from_events")

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.process_events(datetime.now())


class IntValFerroampSensor(KeyedFerroampSensor):
    """Ferroamp integer value Sensor."""

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg = average_int_values(events, self._state_key)
        if avg is None:
            return False
        self._attr_native_value = avg
        return True


class StringValFerroampSensor(KeyedFerroampSensor):
    """Ferroamp string value Sensor."""

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        val = last_string_value(events, self._state_key)
        if val is None:
            return False
        self._attr_native_value = val
        return True


class FloatValFerroampSensor(KeyedFerroampSensor):
    """Ferroamp float value Sensor."""

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg = average_float_values(events, self._state_key)
        if avg is None:
            return False
        self._attr_native_value = avg
        return True


class DcLinkFerroampSensor(KeyedFerroampSensor):
    """Ferroamp DC Voltage value Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfElectricPotential.VOLT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        dc_link = average_dc_link_values(events, self._state_key)
        if dc_link is None:
            return False
        self._attr_native_value = round(dc_link.total, 2)
        self._attr_extra_state_attributes = {
            "neg": round(dc_link.neg, 2),
            "pos": round(dc_link.pos, 2),
        }
        return True


class PercentageFerroampSensor(FloatValFerroampSensor):
    """Ferroamp percentage Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            PERCENTAGE,
            "mdi:battery-low",
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        res = super().update_state_from_events(events)
        if self.state is not None and self.state != "unknown":
            pct = int(float(self.state) / 10) * 10
            if pct <= 90:
                self._attr_icon = icon_for_battery_level(battery_level=pct)
            else:
                self._attr_icon = "mdi:battery"
        return res


class BatteryFerroampSensor(PercentageFerroampSensor):
    """Ferroamp battery Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._attr_device_class = SensorDeviceClass.BATTERY


class TemperatureFerroampSensor(FloatValFerroampSensor):
    """Ferroamp temperature Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfTemperature.CELSIUS,
            "mdi:thermometer",
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT


class CurrentFerroampSensor(FloatValFerroampSensor):
    """Ferroamp current Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfElectricCurrent.AMPERE,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT


class VoltageFerroampSensor(FloatValFerroampSensor):
    """Ferroamp voltage Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfElectricPotential.VOLT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT


class EnergyFerroampSensor(FloatValFerroampSensor):
    """Ferroamp energy in kWh Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfEnergy.KILO_WATT_HOUR,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            state_class=SensorStateClass.TOTAL_INCREASING,
            **kwargs,
        )

    def add_event(self, event: MqttEvent) -> None:
        """Add event, filtering out zero values."""
        if not self.check_presence or self.present(event):
            if self.get_float_value(event) > 0:
                super().add_event(event)
            else:
                _LOGGER.info(
                    "%s value %s seems to be zero. Ignoring",
                    self.entity_id,
                    self.get_value(event),
                )

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg = average_float_values(events, self._state_key)
        if avg is None:
            return False
        val = convert_to_kwh(avg)
        if (
            self._attr_native_value is None
            or (
                isinstance(self._attr_native_value, str)
                and not isfloat(self._attr_native_value)
            )
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
            or val > float(self._attr_native_value)
            or val * 1.1 < float(self._attr_native_value)
        ):
            self._attr_native_value = val
            return True
        return False


class RelayStatusFerroampSensor(KeyedFerroampSensor):
    """Ferroamp relay status Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            None,
            "",
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        temp: str | None = None
        for event in events:
            val = MqttMessageParser.get_int(event, self._state_key)
            if val is not None:
                if val == 0:
                    temp = "closed"
                elif val == 1:
                    temp = "open/disconnected"
                elif val == 2:
                    temp = "precharge"
        if temp is None:
            return False
        self._attr_native_value = temp
        return True


class PowerFerroampSensor(FloatValFerroampSensor):
    """Ferroamp Power Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfPower.WATT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )


class CalculatedPowerFerroampSensor(KeyedFerroampSensor):
    """Ferroamp Power Sensor based on V and A."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        voltage_key: str,
        current_key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            voltage_key,
            UnitOfPower.WATT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._voltage_key = voltage_key
        self._current_key = current_key
        self._attr_unique_id = (
            f"{self.device_id}-{self._voltage_key}-{self._current_key}"
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg_voltage = average_float_values(events, self._voltage_key)
        avg_current = average_float_values(events, self._current_key)

        if avg_voltage is None or avg_current is None:
            return False
        self._attr_native_value = int(round(avg_voltage * avg_current, 0))
        return True


class SinglePhaseFerroampSensor(KeyedFerroampSensor):
    """Single phase Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        phase: str | None,
        unit: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            unit,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        if self._attr_state_class is None:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._phase = phase
        self._attr_unique_id = f"{self.device_id}-{self._state_key}-{self._phase}"

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg = average_single_phase_values(events, self._state_key, self._phase)
        if avg is None:
            return False
        if (
            self._attr_native_value is None
            or (
                isinstance(self._attr_native_value, str)
                and not isfloat(self._attr_native_value)
            )
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
            or avg > float(self._attr_native_value)
            or avg * 1.1 < float(self._attr_native_value)
        ):
            self._attr_native_value = avg
            return True
        return False


class ThreePhaseFerroampSensor(KeyedFerroampSensor):
    """Ferroamp ThreePhase Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        unit: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            unit,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        if self._attr_state_class is None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    def get_phases(self, event: MqttEvent) -> PhaseValues | None:
        """Get phase values from event."""
        return MqttMessageParser.get_phases(event, self._state_key)

    def calculate_value(self, phases: PhaseValues) -> float:
        """Calculate aggregated value from phases."""
        return phases.total

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        avg_phases = average_phase_values(events, self._state_key)
        if avg_phases is None:
            return False
        val = self.calculate_value(avg_phases)
        if (
            self._attr_native_value is None
            or (
                isinstance(self._attr_native_value, str)
                and not isfloat(self._attr_native_value)
            )
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
            or val > float(self._attr_native_value)
            or val * 1.1 < float(self._attr_native_value)
        ):
            self._attr_native_value = val
            self._attr_extra_state_attributes = {
                "L1": round(avg_phases.l1, 2),
                "L2": round(avg_phases.l2, 2),
                "L3": round(avg_phases.l3, 2),
            }
            return True
        return False


class ThreePhaseMinFerroampSensor(ThreePhaseFerroampSensor):
    """ThreePhase Sensor returning minimum phase value (for load balancing)."""

    def calculate_value(self, phases: PhaseValues) -> float:
        """Calculate minimum value across phases."""
        return phases.minimum


class SinglePhaseEnergyFerroampSensor(SinglePhaseFerroampSensor):
    """Single phase energy Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        phase: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            phase,
            UnitOfEnergy.KILO_WATT_HOUR,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            state_class=SensorStateClass.TOTAL_INCREASING,
            **kwargs,
        )

    def get_energy_value(self, event: MqttEvent) -> float | None:
        """Get energy value from event in kWh."""
        val = MqttMessageParser.get_single_phase(event, self._state_key, self._phase)
        if val is not None:
            return round(convert_to_kwh(val), 2)
        return None

    def add_event(self, event: MqttEvent) -> None:
        """Add event, filtering out zero values."""
        val = self.get_energy_value(event)
        if val and val > 0:
            KeyedFerroampSensor.add_event(self, event)
            return

        _LOGGER.info(
            "%s value %s for phase %s seems to be zero or None. Ignoring",
            self.entity_id,
            self.get_energy_value(event),
            self._phase,
        )

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        tmp: float | None = None
        count = 0
        for event in events:
            val = self.get_energy_value(event)
            if val is not None:
                tmp = (tmp or 0) + val
                count += 1
        if tmp is None:
            return False
        avg = tmp / count
        if (
            self._attr_native_value is None
            or (
                isinstance(self._attr_native_value, str)
                and not isfloat(self._attr_native_value)
            )
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
            or avg > float(self._attr_native_value)
            or avg * 1.1 < float(self._attr_native_value)
        ):
            self._attr_native_value = avg
            return True
        return False


class ThreePhaseEnergyFerroampSensor(ThreePhaseFerroampSensor):
    """Three phase energy Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfEnergy.KILO_WATT_HOUR,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            state_class=SensorStateClass.TOTAL_INCREASING,
            **kwargs,
        )

    def add_event(self, event: MqttEvent) -> None:
        """Add event, filtering out zero values."""
        phases = self.get_phases(event)
        if phases is not None and phases.total > 0:
            KeyedFerroampSensor.add_event(self, event)
            return

        _LOGGER.info(
            "%s value %s seems to be zero or None. Ignoring",
            self.entity_id,
            self.get_value(event),
        )

    def get_phases(self, event: MqttEvent) -> PhaseValues | None:
        """Get phase values from event, converted to kWh."""
        phases = super().get_phases(event)
        if phases is not None:
            return PhaseValues(
                l1=round(convert_to_kwh(phases.l1), 2),
                l2=round(convert_to_kwh(phases.l2), 2),
                l3=round(convert_to_kwh(phases.l3), 2),
            )
        return None

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events with kWh conversion."""
        l1: float | None = None
        l2: float | None = None
        l3: float | None = None
        count = 0
        for event in events:
            phases = self.get_phases(event)
            if phases is not None:
                l1 = (l1 or 0) + phases.l1
                l2 = (l2 or 0) + phases.l2
                l3 = (l3 or 0) + phases.l3
                count += 1
        if l1 is None and l2 is None and l3 is None:
            return False
        avg_phases = PhaseValues(
            l1=l1 / count if l1 is not None else 0.0,
            l2=l2 / count if l2 is not None else 0.0,
            l3=l3 / count if l3 is not None else 0.0,
        )
        val = self.calculate_value(avg_phases)
        if (
            self._attr_native_value is None
            or (
                isinstance(self._attr_native_value, str)
                and not isfloat(self._attr_native_value)
            )
            or self._attr_state_class != SensorStateClass.TOTAL_INCREASING
            or val > float(self._attr_native_value)
            or val * 1.1 < float(self._attr_native_value)
        ):
            self._attr_native_value = val
            self._attr_extra_state_attributes = {
                "L1": round(avg_phases.l1, 2),
                "L2": round(avg_phases.l2, 2),
                "L3": round(avg_phases.l3, 2),
            }
            return True
        return False


class SinglePhasePowerFerroampSensor(SinglePhaseFerroampSensor):
    """Single phase power Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        phase: str | None,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            phase,
            UnitOfPower.WATT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT


class ThreePhasePowerFerroampSensor(ThreePhaseFerroampSensor):
    """Three phase power Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        icon: str,
        device_id: str,
        device_name: str,
        interval: int,
        config_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            UnitOfPower.WATT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT


class CommandFerroampSensor(FerroampSensor):
    """Ferroamp command status Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        device_id: str,
        device_name: str,
        config_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            None,
            "mdi:cog-transfer-outline",
            device_id,
            device_name,
            0,
            config_id,
        )
        self._attr_unique_id = f"{self.device_id}_last_cmd"
        self._attr_extra_state_attributes: dict[str, Any] = {}

    def add_request(self, trans_id: str, cmd: str, arg: Any | None) -> None:
        """Add command request."""
        if arg is not None:
            self._attr_native_value = f"{cmd} ({arg})"
        else:
            self._attr_native_value = cmd
        self._attr_extra_state_attributes["transId"] = trans_id
        self._attr_extra_state_attributes["status"] = None
        self._attr_extra_state_attributes["message"] = None
        if self._added:
            self.async_write_ha_state()

    def add_response(self, trans_id: str, status: str, message: str) -> None:
        """Add command response."""
        if self._attr_extra_state_attributes["transId"] == trans_id:
            self._attr_extra_state_attributes["status"] = status
            self._attr_extra_state_attributes["message"] = message
            if self._added:
                self.async_write_ha_state()


class VersionFerroampSensor(FerroampSensor):
    """Ferroamp version Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        device_id: str,
        device_name: str,
        config_id: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            None,
            "mdi:counter",
            device_id,
            device_name,
            0,
            config_id,
        )
        self._attr_unique_id = f"{self.device_id}_extapi-version"
        self._attr_extra_state_attributes: dict[str, Any] = {}

    def set_version(self, version: str) -> None:
        """Set version value."""
        self._attr_native_value = version
        if self._added:
            self.async_write_ha_state()


class FaultcodeFerroampSensor(KeyedFerroampSensor):
    """Ferroamp Faultcode Sensor."""

    def __init__(
        self,
        name: str,
        entity_prefix: str,
        key: str,
        device_id: str,
        device_name: str,
        interval: int,
        fault_codes: list[str],
        config_id: str | None,
        **kwargs: Any,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            key,
            None,
            "mdi:traffic-light",
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs,
        )
        self._fault_codes = fault_codes
        self._attr_extra_state_attributes: dict[str, str] = {}

    def update_state_from_events(self, events: list[MqttEvent]) -> bool:
        """Update state from events."""
        val = last_string_value(events, self._state_key)
        if val is None:
            return False
        self._attr_native_value = val
        x = int(val, 16)
        if x == 0:
            self._attr_extra_state_attributes["0"] = "No errors"
        else:
            if "0" in self._attr_extra_state_attributes:
                del self._attr_extra_state_attributes["0"]
        for i, code in enumerate(self._fault_codes):
            v = 1 << i
            if x & v == v:
                self._attr_extra_state_attributes[f"{i + 1}"] = code
            elif f"{i + 1}" in self._attr_extra_state_attributes:
                del self._attr_extra_state_attributes[f"{i + 1}"]
        return True
