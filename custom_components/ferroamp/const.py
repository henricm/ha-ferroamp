"""Constants for Ferroamp"""

CONF_INTERVAL = "interval"
CONF_PRECISION_BATTERY = "precision_battery"
CONF_PRECISION_CURRENT = "precision_current"
CONF_PRECISION_ENERGY = "precision_energy"
CONF_PRECISION_FREQUENCY = "precision_frequency"
CONF_PRECISION_TEMPERATURE = "precision_temperature"
CONF_PRECISION_VOLTAGE = "precision_voltage"
DATA_DEVICES = "devices"
DATA_LISTENERS = "listeners"
DATA_PREFIXES = "prefixes"
DOMAIN = "ferroamp"
MANUFACTURER = "Ferroamp"

ESO_FAULT_CODES = [
    "The pre-charge from battery to ESO is not reaching the voltage goal prohibiting the closing of the relays.",
    "CAN communication issues between ESO and battery.",
    """This indicates that the SoC limits for the batteries are not configured correctly,
please contact Ferroamp Support for help.""",
    """This indicates that the power limits for the batteries are incorrect or non-optimal.
When controlling batteries via extapi and the system is set in either peak-shaving or
self-consumption modes this flag may be set but it will not affect control.
When not controlling batteries via extapi this indicates that the settings made in EMS Configuration is invalid.""",
    "On-site emergency stop has been triggered.",
    "The DC-link voltage in ESO is so high that it prevents operation.",
    """Indicates that the battery has an alarm or an error flag raised. Please check Battery manufacturer’s manual
for trouble shooting the battery, or call Ferroamp Support.""",
    "Not a fault, just an indication that Battery Manufacturer is not Ferroamp",
]
