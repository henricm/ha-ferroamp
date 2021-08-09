"""Platform for Ferroamp sensors integration."""
import json
import logging
import uuid
from datetime import datetime

from homeassistant import config_entries, core, util
from homeassistant.components import mqtt
from homeassistant.components.sensor import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    SensorEntity,
    STATE_CLASS_MEASUREMENT
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

    ehub = ehub_sensors(slug, name, interval, precision_battery, precision_energy, precision_frequency, config_id)
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

    def update_sensor_from_event(event, sensors, store):
        for sensor in sensors:
            if sensor.unique_id not in store:
                store[sensor.unique_id] = sensor
                _LOGGER.debug(
                    "Registering new sensor %(unique_id)s => %(event)s",
                    dict(unique_id=sensor.unique_id, event=event),
                )
                async_add_entities((sensor,), True)
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
        device_name = f"{name} SSO {sso_id}"
        store, new = get_store(device_id)
        sensors = sso_sensors.get(sso_id)
        if new:
            sensors = sso_sensors[sso_id] = [
                VoltageFerroampSensor(
                    f"{device_name} PV String Voltage",
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
                    "wpv",
                    "mdi:solar-power",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    model=model
                ),
                FaultcodeFerroampSensor(
                    f"{device_name} Faultcode",
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
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                    model=model
                ),
                TemperatureFerroampSensor(
                    f"{device_name} PCB Temperature",
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
        device_name = f"{name} ESO {eso_id}"
        store, new = get_store(device_id)
        sensors = eso_sensors.get(eso_id)
        if new:
            sensors = eso_sensors[eso_id] = [
                VoltageFerroampSensor(
                    f"{device_name} Battery Voltage",
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
                    "wbatprod",
                    "mdi:battery-plus",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    last_reset=util.dt.utc_from_timestamp(0),
                ),
                EnergyFerroampSensor(
                    f"{device_name} Total Energy Consumed",
                    "wbatcons",
                    "mdi:battery-minus",
                    device_id,
                    device_name,
                    interval,
                    precision_energy,
                    config_id,
                    last_reset=util.dt.utc_from_timestamp(0),
                ),
                BatteryFerroampSensor(
                    f"{device_name} State of Charge",
                    "soc",
                    device_id,
                    device_name,
                    interval,
                    precision_battery,
                    config_id,
                ),
                FaultcodeFerroampSensor(
                    f"{device_name} Faultcode",
                    "faultcode",
                    device_id,
                    device_name,
                    interval,
                    FAULT_CODES_ESO,
                    config_id,
                ),
                RelayStatusFerroampSensor(
                    f"{device_name} Relay Status",
                    "relaystatus",
                    device_id,
                    device_name,
                    interval,
                    config_id,
                ),
                TemperatureFerroampSensor(
                    f"{device_name} PCB Temperature",
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
        device_name = f"{name} ESM {esm_id}"
        store, new = get_store(device_id)
        sensors = esm_sensors.get(esm_id)
        if new:
            sensors = esm_sensors[esm_id] = [
                StringValFerroampSensor(
                    f"{device_name} Status",
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
            if sensor.unique_id not in store:
                store[sensor.unique_id] = sensor
                _LOGGER.debug(
                    "Registering new sensor %(unique_id)s",
                    dict(unique_id=sensor.unique_id),
                )
                async_add_entities((sensor,), True)
            sensor.hass = hass
        return sensor

    def get_cmd_sensor(store):
        return get_generic_sensor(store, "cmd", lambda: CommandFerroampSensor(
            f"{name} Control Status",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            config_id
        ))

    def get_version_sensor(store):
        return get_generic_sensor(store, "version", lambda: VersionFerroampSensor(
            f"{name} Extapi Version",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
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

    def __init__(self, name, unit, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        self._attr_name = name
        self._attr_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_id)},
            "name": device_name,
            "manufacturer": MANUFACTURER,
            "model": kwargs.get("model")
        }
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
        self.device_id = device_id
        self.config_id = config_id
        self._attr_state_class = kwargs.get('state_class')
        self._attr_last_reset = kwargs.get('last_reset')

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._attr_state = state.state
        self.hass.data[DOMAIN][DATA_DEVICES][self.config_id][self.device_id][self.unique_id] = self

    def handle_options_update(self, options):
        self._interval = options.get(CONF_INTERVAL)


class KeyedFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp Sensor using a single key to extract state from MQTT-messages."""

    def __init__(self, name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        self._state_key = key
        self._attr_unique_id = f"{self.device_id}-{self._state_key}"
        self.updated = datetime.min
        self.event = {}
        self.events = []

    def add_event(self, event):
        self.events.append(event)
        now = datetime.now()
        delta = (now - self.updated).total_seconds()
        if delta > self._interval and self.entity_id is not None:
            self.process_events(now)

    def process_events(self, now):
        temp = self.events
        self.events = []
        self.updated = now
        self.update_state_from_events(temp)
        self.async_write_ha_state()

    def update_state_from_events(self, events):
        raise Exception("No implementation in base class")

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        self.process_events(datetime.now())


class IntValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp integer value Sensor."""

    def __init__(self, name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events):
        temp = 0
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                temp += float(v["val"])
        self._attr_state = int(temp / len(events))


class StringValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp string value Sensor."""

    def __init__(self, name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events):
        temp = None
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                temp = v["val"]
        if temp is not None:
            self._attr_state = temp


class FloatValFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp float value Sensor."""

    def __init__(self, name, key, unit, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        self._precision = precision

    def update_state_from_events(self, events):
        temp = 0
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                temp += float(v["val"])
        self._attr_state = round(temp / len(events), self._precision)
        if self._precision == 0:
            self._attr_state = int(self._attr_state)


class DcLinkFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp DC Voltage value Sensor."""

    def __init__(self, name, key, icon, device_id, device_name, interval, config_id):
        """Initialize the sensor."""
        super().__init__(name, key, ELECTRIC_POTENTIAL_VOLT, icon, device_id, device_name, interval, config_id)
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def get_voltage(self, event):
        voltage = event.get(self._state_key, None)
        if voltage is not None:
            voltage = dict(neg=float(voltage["neg"]), pos=float(voltage["pos"]))
        return voltage

    def update_state_from_events(self, events):
        neg = pos = 0
        event = self.event
        for e in events:
            event.update(e)
            voltage = self.get_voltage(event)
            if voltage is not None:
                neg += voltage["neg"]
                pos += voltage["pos"]
        self._attr_state = int(neg / len(events) + pos / len(events))
        self._attr_extra_state_attributes = dict(neg=round(float(neg / len(events)), 2),
                                                 pos=round(float(pos / len(events)), 2))


class PercentageFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, key, PERCENTAGE, "mdi:battery-low", device_id, device_name, interval, precision, config_id, **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def update_state_from_events(self, events):
        super().update_state_from_events(events)
        if self.state is not None:
            pct = int(int(self.state) / 10) * 10
            if pct <= 90:
                self._attr_icon = f"mdi:battery-{pct}"
            else:
                self._attr_icon = "mdi:battery"


class BatteryFerroampSensor(PercentageFerroampSensor):
    def __init__(self, name, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, key, device_id, device_name, interval, precision, config_id, **kwargs
        )
        self._attr_device_class = DEVICE_CLASS_BATTERY

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_BATTERY)


class TemperatureFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, key, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, key, TEMP_CELSIUS, "mdi:thermometer", device_id, device_name, interval, precision, config_id, **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_TEMPERATURE)


class CurrentFerroampSensor(FloatValFerroampSensor):
    def __init__(self, name, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name,
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
    def __init__(self, name, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        super().__init__(
            name, key, ELECTRIC_POTENTIAL_VOLT, icon, device_id, device_name, interval, precision, config_id, **kwargs
        )
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_VOLTAGE)


class EnergyFerroampSensor(FloatValFerroampSensor):
    """Representation of a Ferroamp energy in kWh value Sensor."""

    def __init__(self, name, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor"""
        super().__init__(
            name,
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
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def update_state_from_events(self, events):
        temp = 0
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                temp += float(v["val"])
        self._attr_state = round(temp / len(events) / 3600000000, self._precision)
        if self._precision == 0:
            self._attr_state = int(self._attr_state)

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_ENERGY)


class RelayStatusFerroampSensor(KeyedFerroampSensor):
    def __init__(self, name, key, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor"""
        super().__init__(name, key, "", "", device_id, device_name, interval, config_id, **kwargs)

    def update_state_from_events(self, events):
        temp = None
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                val = int(v["val"])
                if val == 0:
                    temp = "closed"
                elif val == 1:
                    temp = "open/disconnected"
                elif val == 2:
                    temp = "precharge"
        if temp is not None:
            self._attr_state = temp


class PowerFerroampSensor(FloatValFerroampSensor):
    """Representation of a Ferroamp Power Sensor."""

    def __init__(self, name, key, icon, device_id, device_name, interval, config_id, **kwargs):
        super().__init__(name, key, POWER_WATT, icon, device_id, device_name, interval, 0, config_id, **kwargs)


class CalculatedPowerFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp Power Sensor based on V and A."""

    def __init__(self, name, voltage_key, current_key, icon, device_id, device_name, interval, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(
            name,
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
        temp_voltage = temp_current = 0
        event = self.event
        for e in events:
            event.update(e)
            voltage = event.get(self._voltage_key, None)
            current = event.get(self._current_key, None)
            if current is not None and voltage is not None:
                temp_voltage += float(voltage["val"])
                temp_current += float(current["val"])

        self._attr_state = int(round(temp_voltage / len(events) * temp_current / len(events), 0))


class ThreePhaseFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp ThreePhase Sensor."""

    def __init__(self, name, key, unit, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon, device_id, device_name, interval, config_id, **kwargs)
        self._attr_state_class = STATE_CLASS_MEASUREMENT
        self._precision = precision

    def get_phases(self, event):
        phases = event.get(self._state_key, None)
        if phases is not None:
            phases = dict(
                L1=float(phases["L1"]), L2=float(phases["L2"]), L3=float(phases["L3"])
            )
        return phases

    def update_state_from_events(self, events):
        l1 = l2 = l3 = 0
        event = self.event
        for e in events:
            event.update(e)
            phases = self.get_phases(event)
            if phases is not None:
                l1 += phases["L1"]
                l2 += phases["L2"]
                l3 += phases["L3"]
        self._attr_state = round(l1 / len(events) + l2 / len(events) + l3 / len(events), self._precision)
        if self._precision == 0:
            self._attr_state = int(self._attr_state)
        self._attr_extra_state_attributes = dict(
            L1=round(float(l1 / len(events)), 2),
            L2=round(float(l2 / len(events)), 2),
            L3=round(float(l3 / len(events)), 2),
        )

class ThreePhaseMinFerroampSensor(ThreePhaseFerroampSensor):
    """Representation of a Ferroamp ThreePhase Sensor returning the minimum phase value as state value. Used in load balancing applications."""

    def update_state_from_events(self, events):
        l1 = l2 = l3 = 0
        event = self.event
        for e in events:
            event.update(e)
            phases = self.get_phases(event)
            if phases is not None:
                l1 += phases["L1"]
                l2 += phases["L2"]
                l3 += phases["L3"]
        self._attr_state = round(min([l1 / len(events), l2 / len(events), l3 / len(events)]), self._precision)
        if self._precision == 0:
            self._attr_state = int(self._attr_state)
        self._attr_extra_state_attributes = dict(
            L1=round(float(l1 / len(events)), 2),
            L2=round(float(l2 / len(events)), 2),
            L3=round(float(l3 / len(events)), 2),
        )

class ThreePhaseEnergyFerroampSensor(ThreePhaseFerroampSensor):
    def __init__(self, name, key, icon, device_id, device_name, interval, precision, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(
            name,
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
        self._attr_state_class = STATE_CLASS_MEASUREMENT

    def get_phases(self, event):
        phases = super().get_phases(event)
        if phases is not None:
            phases = dict(
                L1=round(phases["L1"] / 3600000000, 2),
                L2=round(phases["L2"] / 3600000000, 2),
                L3=round(phases["L3"] / 3600000000, 2),
            )

        return phases

    def handle_options_update(self, options):
        super().handle_options_update(options)
        self._precision = options.get(CONF_PRECISION_ENERGY)


class ThreePhasePowerFerroampSensor(ThreePhaseFerroampSensor):
    def __init__(self, name, key, icon, device_id, device_name, interval, config_id):
        """Initialize the sensor."""
        super().__init__(name, key, POWER_WATT, icon, device_id, device_name, interval, 0, config_id)
        self._attr_state_class = STATE_CLASS_MEASUREMENT


class CommandFerroampSensor(FerroampSensor):
    def __init__(self, name, device_id, device_name, config_id):
        super().__init__(name, None, "mdi:cog-transfer-outline", device_id, device_name, 0, config_id)
        self._attr_unique_id = f"{self.device_id}_last_cmd"
        self._attr_extra_state_attributes = {}

    def add_request(self, trans_id, cmd, arg):
        if arg is not None:
            self._attr_state = f"{cmd} ({arg})"
        else:
            self._attr_state = cmd
        self._attr_extra_state_attributes["transId"] = trans_id
        self._attr_extra_state_attributes["status"] = None
        self._attr_extra_state_attributes["message"] = None
        if self.entity_id is not None:
            self.async_write_ha_state()

    def add_response(self, trans_id, status, message):
        if self._attr_extra_state_attributes["transId"] == trans_id:
            self._attr_extra_state_attributes["status"] = status
            self._attr_extra_state_attributes["message"] = message
            if self.entity_id is not None:
                self.async_write_ha_state()


class VersionFerroampSensor(FerroampSensor):
    def __init__(self, name, device_id, device_name, config_id):
        super().__init__(name, None, "mdi:counter", device_id, device_name, 0, config_id)
        self._attr_unique_id = f"{self.device_id}_extapi-version"
        self._attr_extra_state_attributes = {}

    def set_version(self, version):
        self._attr_state = version
        if self.entity_id is not None:
            self.async_write_ha_state()


class FaultcodeFerroampSensor(KeyedFerroampSensor):
    """Representation of a Ferroamp Faultcode Sensor."""

    def __init__(self, name, key, device_id, device_name, interval, fault_codes, config_id, **kwargs):
        """Initialize the sensor."""
        super().__init__(name, key, "", "mdi:traffic-light", device_id, device_name, interval, config_id, **kwargs)
        self._fault_codes = fault_codes
        self._attr_extra_state_attributes = {}

    def update_state_from_events(self, events):
        temp = None
        event = self.event
        for e in events:
            event.update(e)
            v = event.get(self._state_key, None)
            if v is not None:
                temp = v["val"]
        if temp is not None:
            self._attr_state = temp
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


def ehub_sensors(slug, name, interval, precision_battery, precision_energy, precision_frequency, config_id):
    return [
        FloatValFerroampSensor(
            f"{name} Estimated Grid Frequency",
            "gridfreq",
            FREQUENCY_HERTZ,
            "mdi:sine-wave",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_frequency,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} External Voltage",
            "ul",
            ELECTRIC_POTENTIAL_VOLT,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} Inverter RMS current",
            "il",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-dc",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} Inverter reactive current",
            "ild",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-dc",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} Grid Current",
            "iext",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} Grid Reactive Current",
            "iextd",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} External Active Current",
            "iextq",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhaseFerroampSensor(
            f"{name} Adaptive Current Equalization",
            "iace",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            0,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Grid Power",
            "pext",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Grid Power Reactive",
            "pextreactive",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Inverter Power, active",
            "pinv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Inverter Power, reactive",
            "pinvreactive",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Consumption Power",
            "pload",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhasePowerFerroampSensor(
            f"{name} Consumption Power Reactive",
            "ploadreactive",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} External Energy Produced",
            "wextprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
            last_reset=util.dt.utc_from_timestamp(0),
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} External Energy Consumed",
            "wextconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
            last_reset=util.dt.utc_from_timestamp(0),
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} Inverter Energy Produced",
            "winvprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} Inverter Energy Consumed",
            "winvconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} Load Energy Produced",
            "wloadprodq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
        ),
        ThreePhaseEnergyFerroampSensor(
            f"{name} Load Energy Consumed",
            "wloadconsq",
            "mdi:power-plug",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
        ),
        EnergyFerroampSensor(
            f"{name} Total Solar Energy",
            "wpv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
            last_reset=util.dt.utc_from_timestamp(0),
        ),
        EnergyFerroampSensor(
            f"{name} Battery Energy Produced",
            "wbatprod",
            "mdi:battery-plus",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
            last_reset=util.dt.utc_from_timestamp(0),
        ),
        EnergyFerroampSensor(
            f"{name} Battery Energy Consumed",
            "wbatcons",
            "mdi:battery-minus",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_energy,
            config_id,
            last_reset=util.dt.utc_from_timestamp(0),
        ),
        IntValFerroampSensor(
            f"{name} System State",
            "state",
            "",
            "mdi:traffic-light",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        DcLinkFerroampSensor(
            f"{name} DC Link Voltage",
            "udc",
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        BatteryFerroampSensor(
            f"{name} System State of Charge",
            "soc",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_battery,
            config_id,
        ),
        PercentageFerroampSensor(
            f"{name} System State of Health",
            "soh",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            precision_battery,
            config_id,
        ),
        IntValFerroampSensor(
            f"{name} Apparent power",
            "sext",
            "VA",
            "mdi:transmission-tower",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        PowerFerroampSensor(
            f"{name} Solar Power",
            "ppv",
            "mdi:solar-power",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        PowerFerroampSensor(
            f"{name} Battery Power",
            "pbat",
            "mdi:battery",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT
        ),
        IntValFerroampSensor(
            f"{name} Total rated capacity of all batteries",
            "ratedcap",
            ENERGY_WATT_HOUR,
            "mdi:battery",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            config_id,
        ),
        FloatValFerroampSensor(
            f"{name} Available three phase reactive current for load balancing",
            "iavblq_3p",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            2,
            config_id,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        ThreePhaseMinFerroampSensor(
            f"{name} Available reactive current for load balancing",
            "iavblq",
            ELECTRIC_CURRENT_AMPERE,
            "mdi:current-ac",
            f"{slug}_{EHUB}",
            f"{name} {EHUB_NAME}",
            interval,
            2,
            config_id,
        ),
    ]
