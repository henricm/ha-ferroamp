import pytest

from custom_components.ferroamp.fault_codes import (
    ESO_FAULT_DESCRIPTIONS,
    SSO_FAULT_DESCRIPTIONS,
    EsoFault,
    SsoFault,
    active_fault_descriptions,
    active_fault_names,
    format_fault_state,
    parse_faultcode,
    unknown_fault_bits,
)


def test_parse_faultcode_as_decimal_uint16_string():
    assert parse_faultcode("32") == 32
    assert parse_faultcode(" 544 ") == 544


@pytest.mark.parametrize("value", ["-1", "65536", "not-a-number"])
def test_parse_faultcode_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        parse_faultcode(value)


def test_format_eso_fault_state_with_unknown_bits():
    assert format_fault_state(0, EsoFault) == "Ok"
    assert format_fault_state(32, EsoFault) == "DcLinkVoltageTooHigh"
    assert format_fault_state(544, EsoFault) == "DcLinkVoltageTooHigh|Unknown0x0200"
    assert active_fault_names(544, EsoFault) == ["DcLinkVoltageTooHigh"]
    assert active_fault_descriptions(544, EsoFault, ESO_FAULT_DESCRIPTIONS) == [
        "The DC-link voltage in ESO is so high that it prevents operation."
    ]
    assert unknown_fault_bits(544, EsoFault) == ["0x0200"]


def test_format_sso_fault_state():
    assert format_fault_state(1, SsoFault) == "PvGroundFault"
    assert (
        format_fault_state(1088, SsoFault) == "InternalTemperatureLimit|PowerLimiting"
    )
    assert active_fault_descriptions(1088, SsoFault, SSO_FAULT_DESCRIPTIONS) == [
        "Warning, Limiting current due to internal temperature",
        "Warning, SSO is limiting power, either because of internal temperature "
        "or DC grid voltage level",
    ]
