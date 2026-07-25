# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Home Assistant custom integration for Ferroamp EnergyHub systems. It creates sensors from MQTT messages published by Ferroamp devices (EnergyHub, SSO solar optimizers, ESO battery systems, ESM battery modules).

## Development Commands

```bash
# Install dependencies
pip install -r requirements.dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests with coverage
pytest

# Run a single test
pytest tests/test_sensor.py::test_function_name -v

# Run pre-commit checks manually
pre-commit run --all-files
```

## Code Architecture

### Integration Structure

- `custom_components/ferroamp/__init__.py` - Entry point; sets up MQTT subscriptions for battery control services (`charge`, `discharge`, `autocharge`)
- `custom_components/ferroamp/sensor.py` - Main sensor platform; subscribes to MQTT topics and creates sensors dynamically
- `custom_components/ferroamp/fault_codes.py` - Internal `IntFlag` models and helpers for decoded ESO/SSO fault state sensors
- `custom_components/ferroamp/config_flow.py` - UI-based configuration for the integration
- `custom_components/ferroamp/const.py` - Constants including MQTT topics, legacy fault code messages, and regex patterns

### Sensor Hierarchy

The `sensor.py` contains a hierarchy of sensor classes:

- `FerroampSensor` (base) -> `KeyedFerroampSensor` (adds MQTT key extraction)
  - `FloatValFerroampSensor`, `IntValFerroampSensor`, `StringValFerroampSensor` - Simple value types
  - `ThreePhaseFerroampSensor` - Aggregates L1/L2/L3 phases
  - `SinglePhaseFerroampSensor` - Individual phase values
  - `EnergyFerroampSensor` - Energy accumulation with kWh conversion
  - Specialized: `BatteryFerroampSensor`, `TemperatureFerroampSensor`, `FaultcodeFerroampSensor`, `DecodedFaultcodeFerroampSensor`

### MQTT Topic Structure

Sensors subscribe to topics under a configurable prefix (default: `extapi`):
- `extapi/data/ehub` - EnergyHub data (1s interval)
- `extapi/data/sso` - Solar optimizer data (5s interval)
- `extapi/data/eso` - Battery system data (5s interval)
- `extapi/data/esm` - Battery module data (60s interval)
- `extapi/control/*` - Battery control request/response

### Fault Codes

ESO and SSO devices expose the original `Faultcode` sensor for backwards compatibility. This legacy sensor parses the MQTT value as a decimal `uint16` bitmask and exposes mapped messages as attributes.

New `Fault State` sensors are added beside the legacy sensors for ESO and SSO devices. They parse `faultcode.val` as a decimal `uint16` bitmask, model known bits with `IntFlag` classes in `fault_codes.py`, and expose a human-readable PascalCase state that is visible in Home Assistant history, for example `DcLinkVoltageTooHigh`, `InternalTemperatureLimit|PowerLimiting`, or `Unknown0x0200` for undocumented bits. Supporting attributes include `raw_value`, `value_hex`, `active_messages`, and `unknown_bits`.

SSO `PvGroundFault` is mapped to bit `0x0001` based on Ferroamp support feedback. Keep the SSO mapping in `const.py` and `fault_codes.py` aligned for this bit so the legacy `Faultcode` and decoded `Fault State` sensors report the same PV ground fault.

### Event Processing

Sensors use an interval-based averaging system (default 30s) to avoid overwhelming Home Assistant with 1-second updates. Events are collected and averaged before updating sensor state.

## Pre-commit Hooks

The project uses commitlint with conventional commits format. Commits must follow the pattern: `type(scope): message` (e.g., `feat: add new sensor`, `fix: correct calculation`).

## Testing

Tests use `pytest-homeassistant-custom-component` which provides Home Assistant test fixtures. The `conftest.py` enables custom integration loading and mocks persistent notifications.

Required Python version: 3.14+
