"""Tests for the MQTT parser module."""

from unittest.mock import MagicMock

import pytest

from custom_components.ferroamp.mqtt_parser import (
    ENERGY_CONVERSION_FACTOR,
    CommandParser,
    DcLinkValues,
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


class TestPhaseValues:
    """Tests for PhaseValues dataclass."""

    def test_total(self):
        """Test total property returns sum of all phases."""
        phases = PhaseValues(l1=100.0, l2=200.0, l3=300.0)
        assert phases.total == 600.0

    def test_minimum(self):
        """Test minimum property returns smallest phase value."""
        phases = PhaseValues(l1=100.0, l2=50.0, l3=300.0)
        assert phases.minimum == 50.0

    def test_to_dict(self):
        """Test to_dict method returns correct dictionary."""
        phases = PhaseValues(l1=100.0, l2=200.0, l3=300.0)
        result = phases.to_dict()
        assert result == {"L1": 100.0, "L2": 200.0, "L3": 300.0}

    def test_frozen(self):
        """Test that PhaseValues is immutable."""
        phases = PhaseValues(l1=100.0, l2=200.0, l3=300.0)
        with pytest.raises(AttributeError):
            phases.l1 = 500.0


class TestDcLinkValues:
    """Tests for DcLinkValues dataclass."""

    def test_total(self):
        """Test total property returns pos - neg."""
        dc_link = DcLinkValues(neg=-200.0, pos=400.0)
        assert dc_link.total == 600.0

    def test_frozen(self):
        """Test that DcLinkValues is immutable."""
        dc_link = DcLinkValues(neg=-200.0, pos=400.0)
        with pytest.raises(AttributeError):
            dc_link.neg = -100.0


class TestMqttMessageParser:
    """Tests for MqttMessageParser class."""

    def test_parse_message(self):
        """Test parsing MQTT message payload."""
        msg = MagicMock()
        msg.payload = '{"key": "value", "number": 123}'
        result = MqttMessageParser.parse_message(msg)
        assert result == {"key": "value", "number": 123}

    def test_get_id_present(self):
        """Test getting ID when present in event."""
        event = {"id": {"val": "device123"}}
        assert MqttMessageParser.get_id(event) == "device123"

    def test_get_id_missing(self):
        """Test getting ID when not present in event."""
        event = {"other_key": "value"}
        assert MqttMessageParser.get_id(event) is None

    def test_get_id_no_val(self):
        """Test getting ID when id exists but has no val."""
        event = {"id": {"other": "data"}}
        assert MqttMessageParser.get_id(event) is None

    def test_get_value(self):
        """Test getting raw value from event."""
        event = {"power": {"val": "1234"}}
        result = MqttMessageParser.get_value(event, "power")
        assert result == {"val": "1234"}

    def test_get_value_missing(self):
        """Test getting value when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_value(event, "power") is None

    def test_get_float(self):
        """Test getting float value from event."""
        event = {"voltage": {"val": "230.5"}}
        assert MqttMessageParser.get_float(event, "voltage") == 230.5

    def test_get_float_missing(self):
        """Test getting float when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_float(event, "voltage") is None

    def test_get_int(self):
        """Test getting integer value from event."""
        event = {"state": {"val": "42"}}
        assert MqttMessageParser.get_int(event, "state") == 42

    def test_get_int_from_float(self):
        """Test getting integer from float string."""
        event = {"state": {"val": "42.7"}}
        assert MqttMessageParser.get_int(event, "state") == 42

    def test_get_int_missing(self):
        """Test getting int when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_int(event, "state") is None

    def test_get_string(self):
        """Test getting string value from event."""
        event = {"status": {"val": "running"}}
        assert MqttMessageParser.get_string(event, "status") == "running"

    def test_get_string_missing(self):
        """Test getting string when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_string(event, "status") is None

    def test_get_phases(self):
        """Test getting three-phase values from event."""
        event = {"ul": {"L1": 230.0, "L2": 231.0, "L3": 229.0}}
        result = MqttMessageParser.get_phases(event, "ul")
        assert result == PhaseValues(l1=230.0, l2=231.0, l3=229.0)

    def test_get_phases_missing_key(self):
        """Test getting phases when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_phases(event, "ul") is None

    def test_get_phases_all_none(self):
        """Test getting phases when all phase values are None."""
        event = {"ul": {"L1": None, "L2": None, "L3": None}}
        assert MqttMessageParser.get_phases(event, "ul") is None

    def test_get_phases_partial(self):
        """Test getting phases when some values are None."""
        event = {"ul": {"L1": 230.0, "L2": None, "L3": 229.0}}
        result = MqttMessageParser.get_phases(event, "ul")
        assert result == PhaseValues(l1=230.0, l2=0.0, l3=229.0)

    def test_get_single_phase(self):
        """Test getting single phase value from event."""
        event = {"ul": {"L1": 230.0, "L2": 231.0, "L3": 229.0}}
        assert MqttMessageParser.get_single_phase(event, "ul", "L2") == 231.0

    def test_get_single_phase_missing_key(self):
        """Test getting single phase when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_single_phase(event, "ul", "L1") is None

    def test_get_single_phase_missing_phase(self):
        """Test getting single phase when phase is None."""
        event = {"ul": {"L1": 230.0, "L2": None, "L3": 229.0}}
        assert MqttMessageParser.get_single_phase(event, "ul", "L2") is None

    def test_get_dc_link(self):
        """Test getting DC link values from event."""
        event = {"udc": {"neg": -200.0, "pos": 400.0}}
        result = MqttMessageParser.get_dc_link(event, "udc")
        assert result == DcLinkValues(neg=-200.0, pos=400.0)

    def test_get_dc_link_missing_key(self):
        """Test getting DC link when key is missing."""
        event = {"other": "value"}
        assert MqttMessageParser.get_dc_link(event, "udc") is None

    def test_get_dc_link_missing_neg(self):
        """Test getting DC link when neg is missing."""
        event = {"udc": {"pos": 400.0}}
        assert MqttMessageParser.get_dc_link(event, "udc") is None

    def test_get_dc_link_missing_pos(self):
        """Test getting DC link when pos is missing."""
        event = {"udc": {"neg": -200.0}}
        assert MqttMessageParser.get_dc_link(event, "udc") is None

    def test_key_present_true(self):
        """Test key_present returns True when key exists."""
        event = {"power": {"val": "1234"}}
        assert MqttMessageParser.key_present(event, "power") is True

    def test_key_present_false(self):
        """Test key_present returns False when key missing."""
        event = {"other": "value"}
        assert MqttMessageParser.key_present(event, "power") is False


class TestCommandParser:
    """Tests for CommandParser class."""

    def test_parse_request(self):
        """Test parsing control request message."""
        event = {
            "transId": "abc123",
            "cmd": {"name": "charge", "arg": 5000},
        }
        trans_id, cmd_name, arg = CommandParser.parse_request(event)
        assert trans_id == "abc123"
        assert cmd_name == "charge"
        assert arg == 5000

    def test_parse_request_no_arg(self):
        """Test parsing control request without argument."""
        event = {
            "transId": "abc123",
            "cmd": {"name": "extapiversion"},
        }
        trans_id, cmd_name, arg = CommandParser.parse_request(event)
        assert trans_id == "abc123"
        assert cmd_name == "extapiversion"
        assert arg is None

    def test_parse_response(self):
        """Test parsing control response message."""
        event = {
            "transId": "abc123",
            "status": "ok",
            "msg": "Command executed",
        }
        trans_id, status, message = CommandParser.parse_response(event)
        assert trans_id == "abc123"
        assert status == "ok"
        assert message == "Command executed"

    def test_is_version_response_true(self):
        """Test is_version_response returns True for version message."""
        assert CommandParser.is_version_response("version: 1.2.3") is True

    def test_is_version_response_false(self):
        """Test is_version_response returns False for other messages."""
        assert CommandParser.is_version_response("Command executed") is False

    def test_extract_version(self):
        """Test extracting version from version response."""
        assert CommandParser.extract_version("version: 1.2.3") == "1.2.3"


class TestAverageFunctions:
    """Tests for averaging helper functions."""

    def test_average_float_values(self):
        """Test averaging float values across events."""
        events = [
            {"voltage": {"val": "230.0"}},
            {"voltage": {"val": "232.0"}},
            {"voltage": {"val": "228.0"}},
        ]
        assert average_float_values(events, "voltage") == 230.0

    def test_average_float_values_empty(self):
        """Test averaging with empty event list."""
        assert average_float_values([], "voltage") is None

    def test_average_float_values_missing_key(self):
        """Test averaging when key is missing from events."""
        events = [{"other": {"val": "100"}}]
        assert average_float_values(events, "voltage") is None

    def test_average_int_values(self):
        """Test averaging integer values across events."""
        events = [
            {"state": {"val": "10"}},
            {"state": {"val": "20"}},
            {"state": {"val": "30"}},
        ]
        assert average_int_values(events, "state") == 20

    def test_average_int_values_empty(self):
        """Test averaging integers with empty event list."""
        assert average_int_values([], "state") is None

    def test_average_phase_values(self):
        """Test averaging three-phase values across events."""
        events = [
            {"ul": {"L1": 230.0, "L2": 231.0, "L3": 229.0}},
            {"ul": {"L1": 232.0, "L2": 233.0, "L3": 231.0}},
        ]
        result = average_phase_values(events, "ul")
        assert result.l1 == 231.0
        assert result.l2 == 232.0
        assert result.l3 == 230.0

    def test_average_phase_values_empty(self):
        """Test averaging phases with empty event list."""
        assert average_phase_values([], "ul") is None

    def test_average_single_phase_values(self):
        """Test averaging single phase values across events."""
        events = [
            {"ul": {"L1": 230.0, "L2": 231.0, "L3": 229.0}},
            {"ul": {"L1": 232.0, "L2": 233.0, "L3": 231.0}},
        ]
        assert average_single_phase_values(events, "ul", "L1") == 231.0

    def test_average_single_phase_values_empty(self):
        """Test averaging single phase with empty event list."""
        assert average_single_phase_values([], "ul", "L1") is None

    def test_average_single_phase_values_missing(self):
        """Test averaging when phase is missing from events."""
        events = [{"ul": {"L1": None, "L2": 231.0, "L3": 229.0}}]
        assert average_single_phase_values(events, "ul", "L1") is None

    def test_average_dc_link_values(self):
        """Test averaging DC link values across events."""
        events = [
            {"udc": {"neg": -200.0, "pos": 400.0}},
            {"udc": {"neg": -210.0, "pos": 410.0}},
        ]
        result = average_dc_link_values(events, "udc")
        assert result.neg == -205.0
        assert result.pos == 405.0

    def test_average_dc_link_values_empty(self):
        """Test averaging DC link with empty event list."""
        assert average_dc_link_values([], "udc") is None


class TestLastStringValue:
    """Tests for last_string_value function."""

    def test_last_string_value(self):
        """Test getting last string value from events."""
        events = [
            {"status": {"val": "first"}},
            {"status": {"val": "second"}},
            {"status": {"val": "last"}},
        ]
        assert last_string_value(events, "status") == "last"

    def test_last_string_value_empty(self):
        """Test with empty event list."""
        assert last_string_value([], "status") is None

    def test_last_string_value_missing_key(self):
        """Test when key is missing from events."""
        events = [{"other": {"val": "value"}}]
        assert last_string_value(events, "status") is None

    def test_last_string_value_with_gaps(self):
        """Test when some events are missing the key."""
        events = [
            {"status": {"val": "first"}},
            {"other": {"val": "ignore"}},
            {"status": {"val": "last"}},
        ]
        assert last_string_value(events, "status") == "last"


class TestConvertToKwh:
    """Tests for convert_to_kwh function."""

    def test_convert_to_kwh(self):
        """Test converting µWs to kWh."""
        # 3600000000 µWs = 1 kWh
        assert convert_to_kwh(3600000000) == 1.0

    def test_convert_to_kwh_zero(self):
        """Test converting zero."""
        assert convert_to_kwh(0) == 0.0

    def test_energy_conversion_factor(self):
        """Test the energy conversion factor constant."""
        assert ENERGY_CONVERSION_FACTOR == 3600000000
