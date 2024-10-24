"""Constants for Ferroamp"""

import re

CONF_INTERVAL = "interval"
DATA_DEVICES = "devices"
DATA_LISTENERS = "listeners"
DATA_PREFIXES = "prefixes"
DOMAIN = "ferroamp"
MANUFACTURER = "Ferroamp"

TOPIC_EHUB = "data/ehub"
TOPIC_SSO = "data/sso"
TOPIC_ESO = "data/eso"
TOPIC_ESM = "data/esm"
TOPIC_CONTROL_REQUEST = "control/request"
TOPIC_CONTROL_RESPONSE = "control/response"
TOPIC_CONTROL_RESULT = "control/result"

PLATFORMS = ["sensor"]

EHUB = "ehub"
EHUB_NAME = "EnergyHub"

REGEX_SSO_ID = re.compile(r"^((PS\d+-[A-Z]\d+)-S)?(\d+)$")
REGEX_ESM_ID = re.compile(r"^(.+?)?-?(\d{8})\s*$")

FAULT_CODES_ESO = [
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

FAULT_CODES_SSO = [
    "Unknown fault code",
    "Unknown fault code",
    "Error, PV ground fault",
    "Error, internal voltage unbalance",
    "Warning, PV undervoltage, not possible to sustain MPPT operation",
    "Warning, DC grid voltage too high, SSO will not connect to DC grid",
    "Warning, Limiting current due to internal temperature",
    "Error, Internal power electronics fault",
    "Error, Internal relay test circuit has detected a fault",
    "Error, Memory error, configuration parameters can not be read",
    "Warning, SSO is limiting power, either because of internal temperature or DC grid voltage level",
]
