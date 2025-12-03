"""MQTT message parsing utilities for Ferroamp integration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any

from homeassistant.components import mqtt

_LOGGER = logging.getLogger(__name__)

# Type alias for parsed MQTT event data
MqttEvent = dict[str, Any]


@dataclass(frozen=True)
class PhaseValues:
    """Container for three-phase values."""

    l1: float
    l2: float
    l3: float

    @property
    def total(self) -> float:
        """Return sum of all phases."""
        return self.l1 + self.l2 + self.l3

    @property
    def minimum(self) -> float:
        """Return minimum phase value."""
        return min(self.l1, self.l2, self.l3)

    def to_dict(self) -> dict[str, float]:
        """Return phase values as dictionary."""
        return {"L1": self.l1, "L2": self.l2, "L3": self.l3}


@dataclass(frozen=True)
class DcLinkValues:
    """Container for DC link voltage values."""

    neg: float
    pos: float

    @property
    def total(self) -> float:
        """Return total DC link voltage (pos - neg)."""
        return self.pos - self.neg


class MqttMessageParser:
    """Parser for MQTT messages from Ferroamp devices."""

    @staticmethod
    def parse_message(msg: mqtt.ReceiveMessage) -> MqttEvent:
        """Parse MQTT message payload to dictionary.

        Args:
            msg: The MQTT message received.

        Returns:
            Parsed JSON as dictionary.

        Raises:
            json.JSONDecodeError: If the payload is not valid JSON.
        """
        return json.loads(msg.payload)

    @staticmethod
    def get_id(event: MqttEvent) -> str | None:
        """Extract device ID from event.

        Args:
            event: The parsed MQTT event.

        Returns:
            The device ID string, or None if not present.
        """
        id_val = event.get("id")
        if id_val is not None:
            return id_val.get("val")
        return None

    @staticmethod
    def get_value(event: MqttEvent, key: str) -> dict[str, Any] | None:
        """Get raw value dict for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key to extract.

        Returns:
            The value dictionary containing 'val' key, or None.
        """
        return event.get(key)

    @staticmethod
    def get_float(event: MqttEvent, key: str) -> float | None:
        """Get float value for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key to extract.

        Returns:
            The float value, or None if not present.
        """
        val = event.get(key)
        if val is None:
            return None
        return float(val["val"])

    @staticmethod
    def get_int(event: MqttEvent, key: str) -> int | None:
        """Get integer value for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key to extract.

        Returns:
            The integer value, or None if not present.
        """
        val = event.get(key)
        if val is None:
            return None
        return int(float(val["val"]))

    @staticmethod
    def get_string(event: MqttEvent, key: str) -> str | None:
        """Get string value for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key to extract.

        Returns:
            The string value, or None if not present.
        """
        val = event.get(key)
        if val is None:
            return None
        return val["val"]

    @staticmethod
    def get_phases(event: MqttEvent, key: str) -> PhaseValues | None:
        """Get three-phase values for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key containing phase data.

        Returns:
            PhaseValues dataclass, or None if not present.
        """
        phases = event.get(key)
        if phases is None:
            return None
        l1 = phases.get("L1")
        l2 = phases.get("L2")
        l3 = phases.get("L3")
        if l1 is None and l2 is None and l3 is None:
            return None
        return PhaseValues(
            l1=float(l1) if l1 is not None else 0.0,
            l2=float(l2) if l2 is not None else 0.0,
            l3=float(l3) if l3 is not None else 0.0,
        )

    @staticmethod
    def get_single_phase(event: MqttEvent, key: str, phase: str) -> float | None:
        """Get single phase value for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key containing phase data.
            phase: The phase to extract ("L1", "L2", or "L3").

        Returns:
            The phase value as float, or None if not present.
        """
        phases = event.get(key)
        if phases is None:
            return None
        val = phases.get(phase)
        if val is None:
            return None
        return float(val)

    @staticmethod
    def get_dc_link(event: MqttEvent, key: str) -> DcLinkValues | None:
        """Get DC link voltage values for a key from event.

        Args:
            event: The parsed MQTT event.
            key: The key containing DC link data.

        Returns:
            DcLinkValues dataclass, or None if not present.
        """
        voltage = event.get(key)
        if voltage is None:
            return None
        neg = voltage.get("neg")
        pos = voltage.get("pos")
        if neg is None or pos is None:
            return None
        return DcLinkValues(neg=float(neg), pos=float(pos))

    @staticmethod
    def key_present(event: MqttEvent, key: str) -> bool:
        """Check if a key is present in the event.

        Args:
            event: The parsed MQTT event.
            key: The key to check.

        Returns:
            True if the key exists in the event.
        """
        return event.get(key) is not None


class CommandParser:
    """Parser for control request/response messages."""

    @staticmethod
    def parse_request(event: MqttEvent) -> tuple[str, str, Any | None]:
        """Parse a control request message.

        Args:
            event: The parsed control request event.

        Returns:
            Tuple of (transaction_id, command_name, argument).
        """
        trans_id = event["transId"]
        cmd = event["cmd"]
        cmd_name = cmd["name"]
        arg = cmd.get("arg")
        return trans_id, cmd_name, arg

    @staticmethod
    def parse_response(event: MqttEvent) -> tuple[str, str, str]:
        """Parse a control response message.

        Args:
            event: The parsed control response event.

        Returns:
            Tuple of (transaction_id, status, message).
        """
        trans_id = event["transId"]
        status = event["status"]
        message = event["msg"]
        return trans_id, status, message

    @staticmethod
    def is_version_response(message: str) -> bool:
        """Check if response message is a version response.

        Args:
            message: The response message.

        Returns:
            True if this is a version response.
        """
        return message.startswith("version: ")

    @staticmethod
    def extract_version(message: str) -> str:
        """Extract version string from version response.

        Args:
            message: The version response message.

        Returns:
            The extracted version string.
        """
        return message[9:]


def average_float_values(events: list[MqttEvent], key: str) -> float | None:
    """Calculate average of float values across events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.

    Returns:
        Average value, or None if no valid values found.
    """
    total: float | None = None
    count = 0
    for event in events:
        val = MqttMessageParser.get_float(event, key)
        if val is not None:
            total = (total or 0) + val
            count += 1
    if total is None:
        return None
    return total / count


def average_int_values(events: list[MqttEvent], key: str) -> int | None:
    """Calculate average of integer values across events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.

    Returns:
        Average value (rounded), or None if no valid values found.
    """
    avg = average_float_values(events, key)
    if avg is None:
        return None
    return int(avg)


def average_phase_values(events: list[MqttEvent], key: str) -> PhaseValues | None:
    """Calculate average of three-phase values across events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.

    Returns:
        PhaseValues with averaged values, or None if no valid values found.
    """
    l1: float | None = None
    l2: float | None = None
    l3: float | None = None
    count = 0
    for event in events:
        phases = MqttMessageParser.get_phases(event, key)
        if phases is not None:
            l1 = (l1 or 0) + phases.l1
            l2 = (l2 or 0) + phases.l2
            l3 = (l3 or 0) + phases.l3
            count += 1
    if l1 is None and l2 is None and l3 is None:
        return None
    return PhaseValues(
        l1=l1 / count if l1 is not None else 0.0,
        l2=l2 / count if l2 is not None else 0.0,
        l3=l3 / count if l3 is not None else 0.0,
    )


def average_single_phase_values(
    events: list[MqttEvent], key: str, phase: str
) -> float | None:
    """Calculate average of single phase values across events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.
        phase: The phase to extract ("L1", "L2", or "L3").

    Returns:
        Average value, or None if no valid values found.
    """
    total: float | None = None
    count = 0
    for event in events:
        val = MqttMessageParser.get_single_phase(event, key, phase)
        if val is not None:
            total = (total or 0) + val
            count += 1
    if total is None:
        return None
    return total / count


def average_dc_link_values(events: list[MqttEvent], key: str) -> DcLinkValues | None:
    """Calculate average of DC link values across events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.

    Returns:
        DcLinkValues with averaged values, or None if no valid values found.
    """
    neg: float | None = None
    pos: float | None = None
    count = 0
    for event in events:
        dc_link = MqttMessageParser.get_dc_link(event, key)
        if dc_link is not None:
            neg = (neg or 0) + dc_link.neg
            pos = (pos or 0) + dc_link.pos
            count += 1
    if neg is None and pos is None:
        return None
    return DcLinkValues(
        neg=neg / count if neg is not None else 0.0,
        pos=pos / count if pos is not None else 0.0,
    )


def last_string_value(events: list[MqttEvent], key: str) -> str | None:
    """Get the last string value from a list of events.

    Args:
        events: List of MQTT events.
        key: The key to extract from each event.

    Returns:
        The last non-None string value, or None if no valid values found.
    """
    result: str | None = None
    for event in events:
        val = MqttMessageParser.get_string(event, key)
        if val is not None:
            result = val
    return result


# Energy conversion constant (µWs to kWh)
ENERGY_CONVERSION_FACTOR = 3600000000


def convert_to_kwh(value: float) -> float:
    """Convert energy value from µWs to kWh.

    Args:
        value: Energy value in µWs.

    Returns:
        Energy value in kWh.
    """
    return value / ENERGY_CONVERSION_FACTOR
