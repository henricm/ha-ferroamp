"""Platform for Ferroamp sensors integration."""
import logging
import json

from datetime import datetime
from datetime import timedelta

from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.components import mqtt
from homeassistant.util import slugify

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_IP_ADDRESS,
    CONF_NAME,
    ELECTRICAL_CURRENT_AMPERE,
    ENERGY_WATT_HOUR,
    ENERGY_KILO_WATT_HOUR,
    FREQUENCY_HERTZ,
    POWER_KILO_WATT,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    POWER_WATT,
    VOLT,
    UNIT_PERCENTAGE
)

_LOGGER = logging.getLogger(__name__)

EHUB_TOPIC = "extapi/data/ehub"
SSO_TOPIC = "extapi/data/sso"
ESO_TOPIC = "extapi/data/eso"
ESM_TOPIC = "extapi/data/esm"

INTERVAL = timedelta(days=0, seconds=30)

DATA_FERROAMP_EHUB = "ferroamp_ehub"
DATA_FERROAMP_SSO = "ferroamp_sso"
DATA_FERROAMP_ESO = "ferroamp_eso"
DATA_FERROAMP_ESM = "ferroamp_esm"

def _slug(name):
    return f"sensor.ferroamp_{slugify(name)}"

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    _LOGGER.debug("Setting up ferroamp sensors")

    ehub_sensors = [ThreePhaseFerroampSensor("External Voltage", "ul", VOLT, "mdi:current-ac"),

                    ThreePhaseFerroampSensor("Inverter RMS current", "il", ELECTRICAL_CURRENT_AMPERE, "mdi:current-dc"),
                    ThreePhaseFerroampSensor("Inverter reactive current", "ild", ELECTRICAL_CURRENT_AMPERE, "mdi:current-dc"),
                    ThreePhaseFerroampSensor("Grid Current", "iext", ELECTRICAL_CURRENT_AMPERE, "mdi:current-ac"),
                    ThreePhaseFerroampSensor("Grid Reactive Current", "iextd", ELECTRICAL_CURRENT_AMPERE, "mdi:current-ac"),
                    ThreePhaseFerroampSensor("External Active Current", "iextq", ELECTRICAL_CURRENT_AMPERE, "mdi:current-ac"),

                    ThreePhaseFerroampSensor("Grid Power", "pext", POWER_WATT, "mdi:transmission-tower"),
                    ThreePhaseFerroampSensor("Grid Power Reactive", "pextreactive", POWER_WATT, "mdi:transmission-tower"),
                    ThreePhaseFerroampSensor("Inverter Power, active", "pinv", POWER_WATT, "mdi:solar-power"),
                    ThreePhaseFerroampSensor("Interter Power, reactive", "pinvreactive", POWER_WATT, "mdi:solar-power"),

                    ThreePhaseFerroampSensor("Consumtion Power", "pload", POWER_WATT, "mdi:power-plug"),
                    ThreePhaseFerroampSensor("Consumtion Power Reactive", "ploadreactive", POWER_WATT, "mdi:power-plug"),

                    ThreePhaseEnergyFerroampSensor("External Energy Produced", "wextprodq", "mdi:power-plug"),
                    ThreePhaseEnergyFerroampSensor("External Energy Consumed", "wextconsq", "mdi:power-plug"),
                    ThreePhaseEnergyFerroampSensor("Inverter Energy Produced", "winvprodq", "mdi:power-plug"),
                    ThreePhaseEnergyFerroampSensor("Inverter Energy Consumed", "winvconsq", "mdi:power-plug"),
                    ThreePhaseEnergyFerroampSensor("Load Energy Produced", "wloadprodq", "mdi:power-plug"),
                    ThreePhaseEnergyFerroampSensor("Load Energy Consumed", "wloadconsq", "mdi:power-plug"),

                    EnergyFerroampSensor(f"Total Solar Energy", "wpv", "mdi:solar-power"),
                    EnergyFerroampSensor(f"Battery Energy Produced", "wbatprod", "mdi:solar-power"),
                    EnergyFerroampSensor(f"Battery Energy Consumed", "wbatcons", "mdi:solar-power"),

                    IntValFerroampSensor("System State", "state", "", "mdi:traffic-light"),

                    DcLinkFerroampSensor("DC Link Voltage", "udc", "mdi:current-ac"),

                    IntValFerroampSensor("System State of Charge", "soc", UNIT_PERCENTAGE, "mdi:battery"),
                    IntValFerroampSensor("System State of Health", "soh", UNIT_PERCENTAGE, "mdi:battery"),
                    IntValFerroampSensor("Apparent power", "sext", "VA", "mdi:mdi-transmission-tower"),
                    
                    IntValFerroampSensor("Solar Power", "ppv", POWER_WATT, "mdi:solar-power"),
                    IntValFerroampSensor("Battery Power", "pbat", POWER_WATT, "mdi:battery"),
                    IntValFerroampSensor("Total rated capacity of all batteries", "ratedcap", ENERGY_WATT_HOUR, "mdi:battery"),
                    ]
    eso_sensors = {}
    esm_sensors = []
    sso_sensors = {}

    ehub_store = hass.data.get(DATA_FERROAMP_EHUB)
    if ehub_store is None:
        ehub_store = hass.data[DATA_FERROAMP_EHUB] = {}
    
    sso_store = hass.data.get(DATA_FERROAMP_SSO)
    if sso_store is None:
        sso_store = hass.data[DATA_FERROAMP_SSO] = {}
    
    eso_store = hass.data.get(DATA_FERROAMP_ESO)
    if eso_store is None:
        eso_store = hass.data[DATA_FERROAMP_ESO] = {}

    esm_store = hass.data.get(DATA_FERROAMP_ESM)
    if esm_store is None:
        esm_store = hass.data[DATA_FERROAMP_ESM] = {}

    def update_sensor_from_msg(msg, sensors, store):
        event = json.loads(msg.payload)
        update_sensor_from_event(event, sensors, store)

    def update_sensor_from_event(event, sensors, store):
        for sensor in sensors:
            if sensor.name not in store:
                sensor.hass = hass
                sensor.set_event(event)
                store[sensor.name] = sensor
                _LOGGER.debug(
                    "Registering new sensor %(name)s => %(event)s",
                    dict(name=sensor.name, event=event),
                )
                async_add_entities((sensor,), True)
            else:
                store[sensor.name].set_event(event)

    @callback
    def ehub_event_received(msg):
        update_sensor_from_msg(msg, ehub_sensors, ehub_store)
    def sso_event_received(msg):
        event = json.loads(msg.payload)
        sso_id = event["id"]["val"]
        store = sso_store.get(sso_id)
        sensors = sso_sensors.get(sso_id)
        if store is None:
            store = sso_store[sso_id] = {}
            sensors = sso_sensors[sso_id] = [IntValFerroampSensor(f"SSO {sso_id} PV String Voltage", "upv", VOLT, "mdi:current-dc"),
                       FloatValFerroampSensor(f"SSO {sso_id} PV String Current", "ipv", ELECTRICAL_CURRENT_AMPERE, "mdi:current-dc"),
                       PowerFerroampSensor(f"SSO {sso_id} PV String Power", "upv", "ipv", "mdi:solar-power"),
                       EnergyFerroampSensor(f"SSO {sso_id} Total Energy", "wpv", "mdi:solar-power"),
                       StringValFerroampSensor(f"SSO {sso_id} Faultcode", "faultcode", "", "mdi:traffic-light"),
                       RelayStatusFerroampSensor(f"SSO {sso_id} Relay Status", "relaystatus"),
                       FloatValFerroampSensor(f"SSO {sso_id} PCB Temperature", "temp", TEMP_CELSIUS, "mdi:thermometer")]

        update_sensor_from_event(event, sensors, store)
    
    def eso_event_received(msg):
        event = json.loads(msg.payload)
        eso_id = event["id"]["val"]
        store = sso_store.get(eso_id)
        sensors = sso_sensors.get(eso_id)
        if store is None:
            store = sso_store[eso_id] = {}
            sensors = sso_sensors[eso_id] = [IntValFerroampSensor(f"ESO {eso_id} Battery Voltage", "ubat", VOLT, "mdi:battery"),
                       FloatValFerroampSensor(f"ESO {eso_id} Battery Current", "ibat", ELECTRICAL_CURRENT_AMPERE, "mdi:battery"),
                       PowerFerroampSensor(f"ESO {eso_id} Battery Power", "ubat", "ibat", "mdi:battery"),
                       EnergyFerroampSensor(f"ESO {eso_id} Total Energy Produced", "wbatprod", "mdi:battery"),
                       EnergyFerroampSensor(f"ESO {eso_id} Total Energy Consumed", "wbatcons", "mdi:battery"),
                       BatteryFerroampSensor(f"ESO {eso_id} State of Charge", "soc"),
                       StringValFerroampSensor(f"ESO {eso_id} Faultcode", "faultcode", "", "mdi:traffic-light"),
                       RelayStatusFerroampSensor(f"ESO {eso_id} Relay Status", "relaystatus"),
                       FloatValFerroampSensor(f"ESO {eso_id} PCB Temperature", "temp", TEMP_CELSIUS, "mdi:thermometer")]

        update_sensor_from_event(event, sensors, store)
    

    #def emo_event_received(msg):
    #    update_sensor(msg, emo_sensors, emo_store)
            

    await mqtt.async_subscribe(hass, EHUB_TOPIC, ehub_event_received, 0)
    await mqtt.async_subscribe(hass, SSO_TOPIC, sso_event_received, 0)
    await mqtt.async_subscribe(hass, ESO_TOPIC, eso_event_received, 0)
#    await mqtt.async_subscribe(hass, EMO_TOPIC, async_ehub_event_received, 0)
    
    return True



class FerroampSensor(Entity):
    """Representation of a Ferroamp Sensor."""

    def __init__(self, name, key, unit, icon):
        """Initialize the sensor."""
        self._state = None
        self.entity_id = _slug(name)
        self._name = name
        self._state_key = key
        self._unit_of_measurement = unit
        self._icon = icon
        self.event = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        return self._icon

    def set_event(self, event):
        """Update the sensor with the most recent event."""
        
        if self.event and self.event["ts"] and self.event["ts"]["val"]:
            time_since_last_update = datetime.fromisoformat(event["ts"]["val"].replace("UTC", "+00:00")) - datetime.fromisoformat(self.event["ts"]["val"].replace("UTC", "+00:00"))
            if (time_since_last_update >= INTERVAL):
                self.update_event(event)
            #else:
                #_LOGGER.debug("Not updating event since last update was %(last)s which is %(interval)s ago", dict(last=event["ts"]["val"], interval=time_since_last_update) )
        else:
            self.update_event(event)

    def update_event(self, event):
        _LOGGER.debug(dict(event=event))
        self.event = {}
        self.event.update(event)
        self.async_write_ha_state()

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.event.get(self._state_key, None)
    
    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

class IntValFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp integer value Sensor."""

    def __init__(self, name, key, unit, icon):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon)

    @property
    def state(self):
        """Return the state of the sensor."""
        v = self.event.get(self._state_key, None)
        
        if v != None:
            v = int(float(v["val"]))

        return v

class StringValFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp string value Sensor."""

    def __init__(self, name, key, unit, icon):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon)

    @property
    def state(self):
        """Return the state of the sensor."""
        v = self.event.get(self._state_key, None)
        
        if v != None:
            v = v["val"]

        return v

class FloatValFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp float value Sensor."""

    def __init__(self, name, key, unit, icon):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon)

    @property
    def state(self):
        """Return the state of the sensor."""
        v = self.event.get(self._state_key, None)
        
        if v != None:
            v = round(float(v["val"]), 2)

        return v

class DcLinkFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp DC Voltage value Sensor."""

    def __init__(self, name, key, icon):
        """Initialize the sensor."""
        super().__init__(name, key, VOLT, icon)

    @property
    def state(self):
        """Return the state of the sensor."""
        v = self.event.get(self._state_key, None)
        
        if v != None:
            v = int(float(v["val"]))

        return v

    def get_voltage(self):
        voltage = self.event.get(self._state_key, None)
        if voltage != None:
            voltage = dict(neg=float(voltage["neg"]), pos=float(voltage["pos"]))
        return voltage

    @property
    def state(self):
        """Return the state of the sensor."""
        voltage = self.get_voltage()
        if voltage is None:
            return None
        
        return int(voltage["neg"] + voltage["pos"])

    @property
    def state_attributes(self):
        """Return the state of the sensor."""
        return self.get_voltage()

class BatteryFerroampSensor(IntValFerroampSensor):

    def __init__(self, name, key):
        super().__init__(name, key, UNIT_PERCENTAGE, "mdi:battery")

    @property
    def icon(self):
        if (self.state < 20):
            self._icon = "mdi:battery-low"
        elif (self.state < 70):
            self._icon = "mid:battery-medium"
        else:
            self._icon = "mdi:battery-high"
        
        return self._icon

class EnergyFerroampSensor(IntValFerroampSensor):
    """Representation of a Ferroamp energy in kWh value Sensor."""

    def __init__(self, name, key, icon):
        """Initialize the sensor"""
        super().__init__(name, key, ENERGY_KILO_WATT_HOUR, icon)

    @property
    def state(self):
        """Return the state of the sensor."""
        v = super().state

        if v != None:
            return int(v/3600000000)

        return v

class RelayStatusFerroampSensor(IntValFerroampSensor):
    def __init__(self, name, key):
        """Initialize the sensor"""
        super().__init__(name, key, "", "")

    @property
    def state(self):
        """Return the state of the sensor."""
        v = super().state

        if v == 0:
            v = "closed"
        elif v == 1:
            v = "open/disconnected"
        elif v == 2:
            v = "precharge"

        return v


class PowerFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp Power Sensor based on V and A."""

    def __init__(self, name, voltage_key, current_key, icon):
        """Initialize the sensor."""
        super().__init__(name, voltage_key, POWER_KILO_WATT, icon)
        self._voltage_key = voltage_key
        self._current_key = current_key

    @property
    def state(self):
        """Return the state of the sensor."""
        voltage = self.event.get(self._voltage_key, None)
        current = self.event.get(self._current_key, None)
        if current is None or voltage is None:
            return None
        
        return round(float(voltage["val"]) * float(current["val"]) / 10000, 2)


class ThreePhaseFerroampSensor(FerroampSensor):
    """Representation of a Ferroamp Threephase Sensor."""

    def __init__(self, name, key, unit, icon):
        """Initialize the sensor."""
        super().__init__(name, key, unit, icon)

    def get_phases(self):
        phases = self.event.get(self._state_key, None)
        _LOGGER.debug(phases)
        if phases != None:
            phases = dict(L1=float(phases["L1"]), L2=float(phases["L2"]), L3=float(phases["L3"]))
        return phases

    @property
    def state(self):
        """Return the state of the sensor."""
        phases = self.get_phases()
        if phases is None:
            return None
        
        return int(phases["L1"] + phases["L2"] + phases["L3"])

    @property
    def state_attributes(self):
        """Return the state of the sensor."""
        return self.get_phases()

class ThreePhaseEnergyFerroampSensor(ThreePhaseFerroampSensor):

    def __init__(self, name, key, icon):
        """Initialize the sensor."""
        super().__init__(name, key, ENERGY_KILO_WATT_HOUR, icon)

    def get_phases(self):
        phases = super().get_phases()
        if phases != None:
            phases = dict(L1=int(phases["L1"]/3600000000), L2=int(phases["L2"]/3600000000), L3=int(phases["L3"]/3600000000)) 

        return phases

