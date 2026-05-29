"""Fault code helpers for Ferroamp bitmask values."""

from __future__ import annotations

from collections.abc import Mapping
from enum import IntFlag


class EsoFault(IntFlag):
    """ESO fault bitmask values."""

    PrechargeFailed = 0x0001
    CanCommunication = 0x0002
    SocLimitsInvalid = 0x0004
    PowerLimitsInvalid = 0x0008
    EmergencyStop = 0x0010
    DcLinkVoltageTooHigh = 0x0020
    BatteryAlarm = 0x0040
    NonFerroampBattery = 0x0080


class SsoFault(IntFlag):
    """SSO fault bitmask values."""

    PvGroundFault = 0x0001
    # 0x0002 and 0x0004 are currently undocumented.
    InternalVoltageUnbalance = 0x0008
    PvUndervoltage = 0x0010
    DcGridVoltageTooHigh = 0x0020
    InternalTemperatureLimit = 0x0040
    InternalPowerElectronicsFault = 0x0080
    InternalRelayTestFault = 0x0100
    MemoryError = 0x0200
    PowerLimiting = 0x0400


ESO_FAULT_DESCRIPTIONS: dict[EsoFault, str] = {
    EsoFault.PrechargeFailed: (
        "The pre-charge from battery to ESO is not reaching the voltage goal "
        "prohibiting the closing of the relays."
    ),
    EsoFault.CanCommunication: "CAN communication issues between ESO and battery.",
    EsoFault.SocLimitsInvalid: (
        "This indicates that the SoC limits for the batteries are not configured "
        "correctly, please contact Ferroamp Support for help."
    ),
    EsoFault.PowerLimitsInvalid: (
        "This indicates that the power limits for the batteries are incorrect or "
        "non-optimal."
    ),
    EsoFault.EmergencyStop: "On-site emergency stop has been triggered.",
    EsoFault.DcLinkVoltageTooHigh: (
        "The DC-link voltage in ESO is so high that it prevents operation."
    ),
    EsoFault.BatteryAlarm: (
        "Indicates that the battery has an alarm or an error flag raised."
    ),
    EsoFault.NonFerroampBattery: (
        "Not a fault, just an indication that Battery Manufacturer is not Ferroamp."
    ),
}

SSO_FAULT_DESCRIPTIONS: dict[SsoFault, str] = {
    SsoFault.PvGroundFault: "Error, PV ground fault",
    SsoFault.InternalVoltageUnbalance: "Error, internal voltage unbalance",
    SsoFault.PvUndervoltage: (
        "Warning, PV undervoltage, not possible to sustain MPPT operation"
    ),
    SsoFault.DcGridVoltageTooHigh: (
        "Warning, DC grid voltage too high, SSO will not connect to DC grid"
    ),
    SsoFault.InternalTemperatureLimit: (
        "Warning, Limiting current due to internal temperature"
    ),
    SsoFault.InternalPowerElectronicsFault: "Error, Internal power electronics fault",
    SsoFault.InternalRelayTestFault: (
        "Error, Internal relay test circuit has detected a fault"
    ),
    SsoFault.MemoryError: (
        "Error, Memory error, configuration parameters can not be read"
    ),
    SsoFault.PowerLimiting: (
        "Warning, SSO is limiting power, either because of internal temperature "
        "or DC grid voltage level"
    ),
}


def parse_faultcode(value: str) -> int:
    """Parse an extapi faultcode value as a decimal uint16 string."""
    parsed = int(str(value).strip(), 10)
    if parsed < 0 or parsed > 0xFFFF:
        raise ValueError("faultcode is outside uint16 range")
    return parsed


def known_fault_mask(fault_type: type[IntFlag]) -> int:
    """Return a mask containing all known flags for a fault type."""
    mask = 0
    for fault in fault_type:
        mask |= fault.value
    return mask


def active_fault_names(value: int, fault_type: type[IntFlag]) -> list[str]:
    """Return names for all known active faults."""
    return [fault.name for fault in fault_type if value & fault.value == fault.value]


def unknown_fault_bits(value: int, fault_type: type[IntFlag]) -> list[str]:
    """Return unknown active bit masks as hexadecimal strings."""
    unknown = value & ~known_fault_mask(fault_type)
    bits = []
    bit = 1
    while unknown:
        if unknown & bit:
            bits.append(f"0x{bit:04X}")
            unknown &= ~bit
        bit <<= 1
    return bits


def format_fault_state(value: int, fault_type: type[IntFlag]) -> str:
    """Format a fault bitmask as a Home Assistant state string."""
    if value == 0:
        return "Ok"

    parts = active_fault_names(value, fault_type)
    parts.extend(f"Unknown{bit}" for bit in unknown_fault_bits(value, fault_type))
    return "|".join(parts) if parts else "Unknown"


def active_fault_descriptions(
    value: int,
    fault_type: type[IntFlag],
    descriptions: Mapping[IntFlag, str],
) -> list[str]:
    """Return descriptions for all known active faults."""
    return [
        descriptions[fault]
        for fault in fault_type
        if value & fault.value == fault.value and fault in descriptions
    ]
