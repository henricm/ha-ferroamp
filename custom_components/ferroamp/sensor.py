"""Platform for Ferroamp sensors integration."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from homeassistant import config_entries, core
from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    SensorEntity,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PREFIX,
    ELECTRIC_CURRENT_AMPERE,
    ENERGY_KILO_WATT_HOUR,
    ENERGY_WATT_HOUR,
    FREQUENCY_HERTZ,
    PERCENTAGE,
    POWER_WATT,
    TEMP_CELSIUS,
    ELECTRIC_POTENTIAL_VOLT
)
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import async_get as async_get_entity_reg
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import slugify

from .const import (
    CONF_INTERVAL,
    CONF_PRECISION_BATTERY,
    CONF_PRECISION_CURRENT,
    CONF_PRECISION_ENERGY,
    CONF_PRECISION_FREQUENCY,
    CONF_PRECISION_TEMPERATURE,
    CONF_PRECISION_VOLTAGE,
    DATA_DEVICES,
    DATA_LISTENERS,
    DOMAIN,
    EHUB,
    EHUB_NAME,
    FAULT_CODES_ESO,
    FAULT_CODES_SSO,
    MANUFACTURER,
    REGEX_SSO_ID,
    REGEX_ESM_ID,
    TOPIC_CONTROL_REQUEST,
    TOPIC_CONTROL_RESPONSE,
    TOPIC_CONTROL_RESULT,
    TOPIC_EHUB,
    TOPIC_ESM,
    TOPIC_ESO,
    TOPIC_SSO
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
        hass: core.HomeAssistant,
        config_entry: config_entries.ConfigEntry,
        async_add_entities,
):
    """Setup sensors from a config entry created in the integrations UI."""
    hass.data[DOMAIN].setdefault(DATA_DEVICES, {})
    hass.data[DOMAIN].setdefault(DATA_LISTENERS, {})
    hass.data[DOMAIN][DATA_DEVICES].setdefault(config_entry.unique_id, {})
    hass.data[DOMAIN][DATA_LISTENERS].setdefault(config_entry.unique_id, [])
    listeners = hass.data[DOMAIN][DATA_LISTENERS].get(config_entry.unique_id)
    config = hass.data[DOMAIN][DATA_DEVICES][config_entry.unique_id]
    _LOGGER.debug(
        "Setting up ferroamp sensors for %(prefix)s",
        dict(prefix=config_entry.data[CONF_PREFIX]),
    )
    config_id = config_entry.unique_id
    name = config_entry.data[CONF_NAME]
    slug = slugify(name)

    interval = get_option(config_entry, CONF_INTERVAL, 30)
    precision_battery = get_option(config_entry, CONF_PRECISION_BATTERY, 1)
    precision_current = get_option(config_entry, CONF_PRECISION_CURRENT, 0)
    precision_energy = get_option(config_entry, CONF_PRECISION_ENERGY, 1)
    precision_frequency = get_option(config_entry, CONF_PRECISION_FREQUENCY, 2)
    precision_temperature = get_option(config_entry, CONF_PRECISION_TEMPERATURE, 0)
    precision_voltage = get_option(config_entry, CONF_PRECISION_VOLTAGE, 0)

    listeners.append(config_entry.add_update_listener(options_update_listener))

    entity_registry = async_get_entity_reg(hass)

    ehub = ehub_sensors(
        slug,
        interval,
        precision_battery,
        precision_current,
        precision_energy,
        precision_frequency,
        config_id
    )
    eso_sensors = {}
    esm_sensors = {}
    sso_sensors = {}
    generic_sensors = {}

    def get_store(store_name):
        store = config.get(store_name)
        new = False
        if store is None:
            store = config[store_name] = {}
            new = True
        return store, new

    def register_sensor(sensor, event, store):
        if sensor.unique_id not in store:
            store[sensor.unique_id] = sensor
            _LOGGER.debug(
                "Registering new sensor %(unique_id)s => %(event)s",
                dict(unique_id=sensor.unique_id, event=event),
            )
            async_add_entities((sensor,), True)

    def update_sensor_from_event(event, sensors, store):
        for sensor in sensors:
            register_sensor(sensor, event, store)
            sensor.hass = hass
            sensor.add_event(event)

    @callback
    def ehub_event_received(msg):
        event = json.loads(msg.payload)
        store, _ = get_store(f"{slug}_{EHUB}")
        update_sensor_from_event(event, ehub, store)

    @callback
    def sso_event_received(msg):
        event = json.loads(msg.payload)
        sso_id = event["id"]["val"]
        model = None
        match = REGEX_SSO_ID.match(sso_id)
        if match is not None and match.group(2) is not None:
            migrate_entities(
                sso_id,
                match.group(3),
                ["upv", "ipv", "upv-ipv", "wpv", "faultcode", "relaystatus", "temp"],
                slug,
                entity_registry,
                lambda s, i: build_sso_device_id(s, i)
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
                    f"{device_name} PV String Voltage",
                    slug,
                    "upv",
                    "mdi:current-dc",
                    device_id,
                    device_name,
                    interval,
                    precision_voltage,
                    config_id,
                    model=model
                ),
                CurrentFerroampSensor(
                    f"{device_name} PV String Current",
                    slug,
                    "ipv",
                    "mdi:current-dc",
                    device_id,
                    device_name,
                    interval,
                    precision_current,
                    config_id,
                    model=model
                ),
                CalculatedPowerFerroampSensor(
                    f"{device_name} PV String Power",
                    slug,
                    "upv",
                    "ipv",
                    "mdi:solar-power",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                ),
                EnergyFerroampSensor(
                    f"{device_name} Total Energy",
                    slug,
                    "wpv",
                    "mdi:solar-power",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    model=model,
                    state_class=STATE_CLASS_TOTAL_INCREASING
                ),
                FaultcodeFerroampSensor(
                    f"{device_name} Faultcode",
                    slug,
                    "faultcode",
                    device_id,
                    device_name,
                    interval,
                    FAULT_CODES_SSO,
                    config_id,
                    model=model
                ),
                RelayStatusFerroampSensor(
                    f"{device_name} Relay Status",
                    slug,
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                ),
                TemperatureFerroampSensor(
                    f"{device_name} PCB Temperature",
                    slug,
                    "temp",
                    device_id,
                    device_name,
                    interval,
                    precision_temperature,
                    config_id,
                    model=model
                ),
            ]

        update_sensor_from_event(event, sensors, store)

    @callback
    def eso_event_received(msg):
        event = json.loads(msg.payload)
        eso_id = event["id"]["val"]
        if eso_id == "":
            return
        device_id = f"{slug}_eso_{eso_id}"
        device_name = f"ESO {eso_id}"
        store, new = get_store(device_id)
        sensors = eso_sensors.get(eso_id)
        if new:
            sensors = eso_sensors[eso_id] = [
                VoltageFerroampSensor(
                    f"{device_name} Battery Voltage",
                    slug,
                    "ubat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    precision_voltage,
                    config_id,
                ),
                CurrentFerroampSensor(
                    f"{device_name} Battery Current",
                    slug,
                    "ibat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    precision_current,
                    config_id
                ),
                CalculatedPowerFerroampSensor(
                    f"{device_name} Battery Power",
                    slug,
                    "ubat",
                    "ibat",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                EnergyFerroampSensor(
                    f"{device_name} Total Energy Produced",
                    slug,
                    "wbatprod",
                    "mdi:battery-plus",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    state_class=STATE_CLASS_TOTAL_INCREASING,
                ),
                EnergyFerroampSensor(
                    f"{device_name} Total Energy Consumed",
                    slug,
                    "wbatcons",
                    "mdi:battery-minus",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    state_class=STATE_CLASS_TOTAL_INCREASING,
                ),
                BatteryFerroampSensor(
                    f"{device_name} State of Charge",
                    slug,
                    "soc",
                    device_id,
                    device_name,
                    interval,
                    precision_battery,
                    config_id,
                ),
                FaultcodeFerroampSensor(
                    f"{device_name} Faultcode",
                    slug,
                    "faultcode",
                    device_id,
                    device_name,
                    interval,
                    FAULT_CODES_ESO,
                    config_id,
                ),
                RelayStatusFerroampSensor(
                    f"{device_name} Relay Status",
                    slug,
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                TemperatureFerroampSensor(
                    f"{device_name} PCB Temperature",
                    slug,
                    "temp",
                    device_id,
                    device_name,
                    interval,
                    precision_temperature,
                    config_id
                ),
            ]

        update_sensor_from_event(event, sensors, store)

    @callback
    def esm_event_received(msg):
        event = json.loads(msg.payload)
        esm_id = event["id"]["val"]
        model = None
        match = REGEX_ESM_ID.match(esm_id)
        if match is not None and match.group(2) is not None and match.group(1) is not None:
            migrate_entities(
                esm_id,
                match.group(2),
                ["status", "soh", "soc", "ratedCapacity", "ratedPower"],
                slug,
                entity_registry,
                lambda s, i: build_esm_device_id(s, i)
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
                    f"{device_name} Status",
                    slug,
                    "status",
                    "",
                    "mdi:traffic-light",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                ),
                PercentageFerroampSensor(
                    f"{device_name} State of Health",
                    slug,
                    "soh",
                    device_id,
                    device_name,
                    interval,
                    precision_battery,
                    config_id,
                    model=model
                ),
                BatteryFerroampSensor(
                    f"{device_name} State of Charge",
                    slug,
                    "soc",
                    device_id,
                    device_name,
                    interval,
                    precision_battery,
                    config_id,
                    model=model
                ),
                IntValFerroampSensor(
                    f"{device_name} Rated Capacity",
                    slug,
                    "ratedCapacity",
                    ENERGY_WATT_HOUR,
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                ),
                PowerFerroampSensor(
                    f"{device_name} Rated Power",
                    slug,
                    "ratedPower",
                    "mdi:battery",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                )
            ]

        update_sensor_from_event(event, sensors, store)

    def get_generic_sensor(store, sensor_type, sensor_creator):
        sensor = generic_sensors.get(sensor_type)
        if sensor is None:
            sensor = sensor_creator()
            generic_sensors[sensor_type] = sensor
            register_sensor(sensor, None, store)
            sensor.hass = hass
        return sensor

    def get_cmd_sensor(store):
        return get_generic_sensor(store, "cmd", lambda: CommandFerroampSensor(
            "Control Status",
            slug,
            f"{slug}_{EHUB}",
            EHUB_NAME,
            config_id
        ))

    def get_version_sensor(store):
        return get_generic_sensor(store, "version", lambda: VersionFerroampSensor(
            "Extapi Version",
            slug,
            f"{slug}_{EHUB}",
            EHUB_NAME,
            config_id
        ))

    @callback
    def ehub_request_received(msg):
        command = json.loads(msg.payload)
        store, _ = get_store(f"{slug}_{EHUB}")
        sensor = get_cmd_sensor(store)
        trans_id = command["transId"]
        cmd = command["cmd"]
        cmd_name = cmd["name"]
        arg = cmd.get("arg")
        sensor.add_request(trans_id, cmd_name, arg)

    @callback
    def ehub_response_received(msg):
        response = json.loads(msg.payload)
        trans_id = response["transId"]
        status = response["status"]
        message = response["msg"]
        store, _ = get_store(f"{slug}_{EHUB}")
        if message.startswith("version: "):
            sensor = get_version_sensor(store)
            sensor.set_version(message[9:])
        else:
            sensor = get_cmd_sensor(store)
            sensor.add_response(trans_id, status, message)

    store, _ = get_store(f"{slug}_{EHUB}")
    get_version_sensor(store)

    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_EHUB}", ehub_event_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_SSO}", sso_event_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_ESO}", eso_event_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_ESM}", esm_event_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_REQUEST}", ehub_request_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_RESPONSE}", ehub_response_received, 0
    ))
    listeners.append(await mqtt.async_subscribe(
        hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_RESULT}", ehub_response_received, 0
    ))

    payload = {"transId": str(uuid.uuid1()), "cmd": {"name": "extapiversion"}}
    mqtt.async_publish(hass, f"{config_entry.data[CONF_PREFIX]}/{TOPIC_CONTROL_REQUEST}", json.dumps(payload))

    return True


def get_option(config_entry, key, default):
    value = config_entry.options.get(key)
    if value is None:
        value = default
    return value


def build_sso_device_id(slug, sso_id):
    return f"{slug}_sso_{sso_id}"


def build_esm_device_id(slug, eso_id):
    return f"{slug}_esm_{eso_id}"


def migrate_entities(old_id, new_id, keys, slug, entity_registry, build_device_id):
    for key in keys:
        old_entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{build_device_id(slug, old_id)}-{key}"
        )
        if old_entity_id is not None:
            entity_registry.async_update_entity(
                old_entity_id, new_unique_id=f"{build_device_id(slug, new_id)}-{key}"
            )


async def options_update_listener(hass, entry):
    """Handle options update."""
    config = hass.data[DOMAIN][DATA_DEVICES][entry.unique_id]
    for device in config.values():
        for sensor in device.values():
            sensor.handle_options_update(entry.options)


class FerroampSensor(SensorEntity, RestoreEntity):
    """Representation of a Ferroamp Sensor."""

    def __init__(self, name, entity_prefix, unit: str | None, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=kwargs.get("model")
        )
        self._attr_should_poll = False
        if unit == ENERGY_KILO_WATT_HOUR:
            self._attr_device_class = DEVICE_CLASS_ENERGY
        elif unit == POWER_WATT:
            self._attr_device_class = DEVICE_CLASS_POWER
        elif unit == ELECTRIC_POTENTIAL_VOLT:
            self._attr_device_class = DEVICE_CLASS_VOLTAGE
        elif unit == ELECTRIC_CURRENT_AMPERE:
            self._attr_device_class = DEVICE_CLASS_CURRENT
        elif unit == TEMP_CELSIUS:
            self._attr_device_class = DEVICE_CLASS_TEMPERATURE
        self._interval = interval
        entity_id = slugify(name)
        self.entity_id = f"sensor.{entity_prefix}_{entity_id}"
        self.device_id = device_id
        self.config_id = config_id
        self._attr_state_class = kwargs.get('state_class')
        self._added = False

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_native_value = state.state
        self.hass.data[DOMAIN][DATA_DEVICES][self.config_id][self.device_id][self.unique_id] = self
        self._added = True

    def handle_options_update(self, options):
        self._interval = options.get(CONF_INTERVAL)


class KeyedFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp Sensor using a single key to extract state from MQTT-messages."""

    def __init__(self, name, entity_prefix, key, unit: str | None, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        self._state_key = key
        self._attr_unique_id = f"{self.device_id}-{self._state_key}"
        self.updated = datetime.min
        self.events = []

    def add_event(self, event):
        self.events.append(event)
        now = datetime.now()
        delta = (now - self.updated).total_seconds()
        if delta > self._interval and self._added:
            self.process_events(now)

    def process_events(self, now):
        temp = self.events
        self.events = []
        self.updated = now
        if len(temp) != 0:
            if self.update_state_from_events(temp):
                self.async_write_ha_state()

    def update_state_from_events(self, events) -> bool:
        raise Exception("No implementation in base class")

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.process_events(datetime.now())


class IntValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp integer value Sensor."""

    def __init__(self, name, entity_prefix, key, unit: str | None, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events) -> bool:
        temp = None
        count = 0
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                count += 1
                temp = (temp or 0) + float(v["val"])
        if temp is None:
            return False
        else:
            self._attr_native_value = int(temp / count)
            return True


class StringValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp string value Sensor."""

    def __init__(self, name, entity_prefix, key, unit: str | None, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events) -> bool:
        temp = None
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                temp = v["val"]
        if temp is None:
            return False
        else:
            self._attr_native_value = temp
            return True


class FloatValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp float value Sensor."""

    def __init__(self, name, entity_prefix, key, unit: str | None, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        self._precision = precision

    def update_state_from_events(self, events) -> bool:
        temp = None
        count = 0
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                count += 1
                temp = (temp or 0) + float(v["val"])
        if temp is None:
            return False
        else:
            self._attr_native_value = round(temp / count, self._precision)
            if self._precision == 0:
                self._attr_native_value = int(self._attr_native_value)
            return True


class DcLinkFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp DC Voltage value Sensor."""

    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, config_id):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, ELECTRIC_POTENTIAL_VOLT, icon, device_id, device_name, interval, config_id)
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def get_voltage(self, event):
        voltage = event.get(self._state_key, None)
        if voltage is not None:
            voltage = dict(neg=float(voltage["neg"]), pos=float(voltage["pos"]))
        return voltage

    def update_state_from_events(self, events):
        neg = pos = None
        count = 0
        for event in events:
            voltage = self.get_voltage(event)
            if voltage is not None:
                neg = (neg or 0) + voltage["neg"]
                pos = (pos or 0) + voltage["pos"]
                count += 1
        if neg is None and pos is None:
            return False
        else:
            self._attr_native_value = int(neg / count + pos / count)
            self._attr_extra_state_attributes = dict(neg=round(float(neg / count), 2),
                                                     pos=round(float(pos / count), 2))
            return True


class PercentageFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, entity_prefix, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, entity_prefix, key, PERCENTAGE, "mdi:battery-low", device_id, device_name, interval, precision, config_id,
            **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def update_state_from_events(self, events):
        res = super().update_state_from_events(events)
        if self.state is not None:
            pct = int(float(self.state) / 10) * 10
            if pct <= 90:
                self._attr_icon = f"mdi:battery-{pct}"
            else:
                self._attr_icon = "mdi:battery"
        return res


class BatteryFerroampSensor(PercentageFerroampSensor):
    def __init__(self, name, entity_prefix, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, entity_prefix, key, device_id, device_name, interval, precision, config_id, **kwargs
        )
        self._attr_device_class = DEVICE_CLASS_BATTERY

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_BATTERY)


class TemperatureFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, entity_prefix, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, entity_prefix, key, TEMP_CELSIUS, "mdi:thermometer", device_id, device_name, interval, precision, config_id,
            **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_TEMPERATURE)


class CurrentFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name,
            entity_prefix,
            key,
            ELECTRIC_CURRENT_AMPERE,
            icon,
            device_id,
            device_name,
            interval,
            precision,
            config_id,
            **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_CURRENT)


class VoltageFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, entity_prefix, key, ELECTRIC_POTENTIAL_VOLT, icon, device_id, device_name, interval, precision, config_id,
            **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_VOLTAGE)


class EnergyFerroampSensor(FloatValFerroampSensor):
    """Representation of a Ferroamp energy in kWh value Sensor."""

    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor"""
        super().__init__(
            name,
            entity_prefix,
            key,
            ENERGY_KILO_WATT_HOUR,
            icon,
            device_id,
            device_name,
            interval,
            precision,
            config_id,
            **kwargs
        )

    def update_state_from_events(self, events):
        temp = None
        count = 0
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                temp = (temp or 0) + float(v["val"])
                count += 1
        if temp is None:
            return False
        else:
            val = round(temp / count / 3600000000, self._precision)
            if self._attr_native_value is None\
                    or (isinstance(self._attr_native_value, str) and not self.isfloat(self._attr_native_value))\
                    or self._attr_state_class != STATE_CLASS_TOTAL_INCREASING\
                    or val > float(self._attr_native_value):
                self._attr_native_value = val
                if self._precision == 0:
                    self._attr_native_value = int(self._attr_native_value)
                return True
            else:
                return False

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_ENERGY)

    def isfloat(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False


class RelayStatusFerroampSensor(KeyedFerroampSensor):
    def __init__(self, name, entity_prefix, key, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor"""
        super().__init__(name, entity_prefix, key, None, "", device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events):
        temp = None
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                val = int(v["val"])
                if val == 0:
                    temp = "closed"
                elif val == 1:
                    temp = "open/disconnected"
                elif val == 2:
                    temp = "precharge"
        if temp is None:
            return False
        else:
            self._attr_native_value = temp
            return True


class PowerFerroampSensor(FloatValFerroampSensor):
    """Representation of a Ferroamp Power Sensor."""

    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, config_id, **kwargs):
        super().__init__(name, entity_prefix, key, POWER_WATT, icon, device_id, device_name, interval, 0, config_id, **kwargs)


class CalculatedPowerFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp Power Sensor based on V and A."""

    def __init__(self, name, entity_prefix, voltage_key, current_key, icon, device_id, device_name, interval, config_id,
                 **kwargs):
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix,
            voltage_key,
            POWER_WATT,
            icon,
            device_id,
            device_name,
            interval,
            config_id,
            **kwargs
        )
        self._voltage_key = voltage_key
        self._current_key = current_key
        self._attr_unique_id = f"{self.device_id}-{self._voltage_key}-{self._current_key}"
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def update_state_from_events(self, events):
        temp_voltage = temp_current = None
        count = 0
        for event in events:
            voltage = event.get(self._voltage_key, None)
            current = event.get(self._current_key, None)
            if current is not None and voltage is not None:
                temp_voltage = (temp_voltage or 0) + float(voltage["val"])
                temp_current = (temp_current or 0) + float(current["val"])
                count += 1

        if temp_voltage is None and temp_current is None:
            return False
        else:
            self._attr_native_value = int(round(temp_voltage / count * temp_current / count, 0))
            return True


class ThreePhaseFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp ThreePhase Sensor."""

    def __init__(self, name, entity_prefix, key, unit: str | None, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        if self._attr_state_class is None:
            self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._precision = precision

    def get_phases(self, event):
        phases = event.get(self._state_key, None)
        if phases is not None and (phases["L1"] is not None or phases["L2"] is not None or phases["L3"] is not None):
            phases = dict(
                L1=float(phases["L1"]), L2=float(phases["L2"]), L3=float(phases["L3"])
            )
            return phases
        return None

    def calculate_value(self, l1, l2, l3, count):
        return round(l1 / count + l2 / count + l3 / count, self._precision)

    def update_state_from_events(self, events):
        l1 = l2 = l3 = None
        count = 0
        for event in events:
            phases = self.get_phases(event)
            if phases is not None:
                l1 = (l1 or 0) + phases["L1"]
                l2 = (l2 or 0) + phases["L2"]
                l3 = (l3 or 0) + phases["L3"]
                count += 1
        if l1 is None and l2 is None and l3 is None:
            return False
        else:
            self._attr_native_value = self.calculate_value(l1, l2, l3, count)
            if self._precision == 0:
                self._attr_native_value = int(self._attr_native_value)
            self._attr_extra_state_attributes = dict(
                L1=round(float(l1 / count), 2),
                L2=round(float(l2 / count), 2),
                L3=round(float(l3 / count), 2),
            )
            return True


class ThreePhaseMinFerroampSensor(ThreePhaseFerroampSensor):
    """Representation of a Ferroamp ThreePhase Sensor returning the minimum phase value as state value.
     Used in load balancing applications."""

    def calculate_value(self, l1, l2, l3, count):
        return round(min([l1 / count, l2 / count, l3 / count]), self._precision)

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_CURRENT)


class ThreePhaseEnergyFerroampSensor(ThreePhaseFerroampSensor):
    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(
            name,
            entity_prefix, key,
            ENERGY_KILO_WATT_HOUR,
            icon,
            device_id,
            device_name,
            interval,
            precision,
            config_id,
            **kwargs
        )

    def get_phases(self, event):
        phases = super().get_phases(event)
        if phases is not None and (phases["L1"] is not None or phases["L2"] is not None or phases["L3"] is not None):
            phases = dict(
                L1=round(phases["L1"] / 3600000000, 2),
                L2=round(phases["L2"] / 3600000000, 2),
                L3=round(phases["L3"] / 3600000000, 2),
            )
            return phases
        return None

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_ENERGY)


class ThreePhasePowerFerroampSensor(ThreePhaseFerroampSensor):
    def __init__(self, name, entity_prefix, key, icon, device_id, device_name, interval, config_id):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, POWER_WATT, icon, device_id, device_name, interval, 0, config_id)
        self._attr_state_class = STATE_CLASS_MEASUREMENT


class CommandFerroampSensor(FerroampSensor):
    def __init__(self, name, entity_prefix, device_id, device_name, config_id):
        super().__init__(name, entity_prefix, None, "mdi:cog-transfer-outline", device_id, device_name, 0, config_id)
        self._attr_unique_id = f"{self.device_id}_last_cmd"
        self._attr_extra_state_attributes = {}

    def add_request(self, trans_id, cmd, arg):
        if arg is not None:
            self._attr_native_value = f"{cmd} ({arg})"
        else:
            self._attr_native_value = cmd
        self._attr_extra_state_attributes["transId"] = trans_id
        self._attr_extra_state_attributes["status"] = None
        self._attr_extra_state_attributes["message"] = None
        if self._added:
            self.async_write_ha_state()

    def add_response(self, trans_id, status, message):
        if self._attr_extra_state_attributes["transId"] == trans_id:
            self._attr_extra_state_attributes["status"] = status
            self._attr_extra_state_attributes["message"] = message
            if self._added:
                self.async_write_ha_state()


class VersionFerroampSensor(FerroampSensor):
    def __init__(self, name, entity_prefix, device_id, device_name, config_id):
        super().__init__(name, entity_prefix, None, "mdi:counter", device_id, device_name, 0, config_id)
        self._attr_unique_id = f"{self.device_id}_extapi-version"
        self._attr_extra_state_attributes = {}

    def set_version(self, version):
        self._attr_native_value = version
        if self._added:
            self.async_write_ha_state()


class FaultcodeFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp Faultcode Sensor."""

    def __init__(self, name, entity_prefix, key, device_id, device_name, interval, fault_codes, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, entity_prefix, key, None, "mdi:traffic-light", device_id, device_name, interval, config_id,
                         **kwargs)
        self._fault_codes = fault_codes
        self._attr_extra_state_attributes = {}

    def update_state_from_events(self, events):
        temp = None
        for event in events:
            v = event.get(self._state_key, None)
            if v is not None:
                temp = v["val"]
        if temp is None:
            return False
        else:
            self._attr_native_value = temp
            x = int(temp, 16)
            if x == 0:
                self._attr_extra_state_attributes[0] = "No errors"
            else:
                if 0 in self._attr_extra_state_attributes:
                    del self._attr_extra_state_attributes[0]
                for i, code in enumerate(self._fault_codes):
                    v = 1 << i
                    if x & v == v:
                        self._attr_extra_state_attributes[i + 1] = code
                    elif i + 1 in self._attr_extra_state_attributes:
                        del self._attr_extra_state_attributes[i + 1]
            return True


def ehub_sensors(slug, interval, precision_battery, precision_current, precision_energy, precision_frequency,
                 config_id):
    return [
        FloatValFerroampSensor(
            "Estimated Grid Frequency",
            slug,
            "gridfreq",
            FREQUENCY_HERTZ,
            "mdi:sine-wave",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_frequency,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "External Voltage",
            slug,
            "ul",
            ELECTRIC_POTENTIAL_VOLT,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "Inverter RMS current",
            slug,
            "il",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-dc",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "Inverter reactive current",
            slug,
            "ild",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-dc",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "Grid Current",
            slug,
            "iext",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "Grid Reactive Current",
            slug,
            "iextd",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "External Active Current",
            slug,
            "iextq",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            "Adaptive Current Equalization",
            slug,
            "iace",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            0,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Grid Power",
            slug,
            "pext",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Grid Power Reactive",
            slug,
            "pextreactive",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Inverter Power, active",
            slug,
            "pinv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Inverter Power, reactive",
            slug,
            "pinvreactive",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Consumption Power",
            slug,
            "pload",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            "Consumption Power Reactive",
            slug,
            "ploadreactive",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            "External Energy Produced",
            slug,
            "wextprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
            state_class=STATE_CLASS_TOTAL_INCREASING,
        ),
        ThreePhaseEnergyFerroampSensor(
            "External Energy Consumed",
            slug,
            "wextconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
            state_class=STATE_CLASS_TOTAL_INCREASING,
        ),
        ThreePhaseEnergyFerroampSensor(
            "Inverter Energy Produced",
            slug,
            "winvprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            "Inverter Energy Consumed",
            slug,
            "winvconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            "Load Energy Produced",
            slug,
            "wloadprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            "Load Energy Consumed",
            slug,
            "wloadconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
        ),
        EnergyFerroampSensor(
            "Total Solar Energy",
            slug,
            "wpv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
            state_class=STATE_CLASS_TOTAL_INCREASING,
        ),
        EnergyFerroampSensor(
            "Battery Energy Produced",
            slug,
            "wbatprod",
            "mdi:battery-plus",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
            state_class=STATE_CLASS_TOTAL_INCREASING,
        ),
        EnergyFerroampSensor(
            "Battery Energy Consumed",
            slug,
            "wbatcons",
            "mdi:battery-minus",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_energy,
            config_id,
            state_class=STATE_CLASS_TOTAL_INCREASING,
        ),
        IntValFerroampSensor(
            "System State",
            slug,
            "state",
            "",
            "mdi:traffic-light",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        DcLinkFerroampSensor(
            "DC Link Voltage",
            slug,
            "udc",
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        BatteryFerroampSensor(
            "System State of Charge",
            slug,
            "soc",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_battery,
            config_id,
        ),
        PercentageFerroampSensor(
            "System State of Health",
            slug,
            "soh",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_battery,
            config_id,
        ),
        IntValFerroampSensor(
            "Apparent power",
            slug,
            "sext",
            "VA",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        PowerFerroampSensor(
            "Solar Power",
            slug,
            "ppv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        PowerFerroampSensor(
            "Battery Power",
            slug,
            "pbat",
            "mdi:battery",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT
        ),
        IntValFerroampSensor(
            "Total rated capacity of all batteries",
            slug,
            "ratedcap",
            ENERGY_WATT_HOUR,
            "mdi:battery",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            config_id,
        ),
        FloatValFerroampSensor(
            "Available three phase active current for load balancing",
            slug,
            "iavblq_3p",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_current,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        ThreePhaseMinFerroampSensor(
            "Available active current for load balancing",
            slug,
            "iavblq",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_current,
            config_id,
        ),
         ThreePhaseMinFerroampSensor(
            "Available RMS current for load balancing",
            slug,
            "iavbl",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            EHUB_NAME,
            interval,
            precision_current,
            config_id,
        ),
    ]
