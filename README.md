[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)
[![Join the chat at https://gitter.im/ha-ferroamp/community](https://img.shields.io/gitter/room/henricm/ha-ferroamp?style=for-the-badge)](https://gitter.im/ha-ferroamp/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

# Home assistant sensors for Ferroamp EnergyHub
This is still very much still work in progress, so please use this component with caution.

Ferroamp MQTT support sends updates to these topics:

 * extapi/data/ehub (interval 1s)
 * extapi/data/eso (interval 5s)
 * extapi/data/sso (interval 5s)
 * extapi/data/esm (interval 60s)

## Prerequisites
- Home assistant `2021.7`
- Enable Ferroamp MQTT by contacting [Ferroamp Support](https://ferroamp.com/sv/kontakt/) to get the username and password for your Energy MQTT broker.
- Enable MQTT in Home assistant and set the broker to your Ferroamp Energy IP and configure it with your username and password received from Ferroamp (or setup a bridge-connection if you already have an MQTT-server, see the `Configuring Bridges`-section in the [Mosquitto documentation](https://mosquitto.org/man/mosquitto-conf-5.html)).

### Install using HACS (recommended)
The repository is compatible with HACS (Home Assistant Community Store).

Install HACS and add the repository to the Custom repositories under HACS Settings tab.

* https://hacs.xyz/docs/installation/manual
   * https://hacs.xyz/docs/basic/getting_started

### Git installation

1. Make sure you have git installed on your machine.
2. Navigate to you home assistant configuration folder.
3. Execute the following command: `git clone https://github.com/henricm/ha-ferroamp.git`
4. Create a `custom_components` folder if it does not exist, and cd into it.
5. Create a symbolic link by executing `ln -s ../ha-ferroamp/custom_components/ferroamp`

## Setup

1. Add the `Ferroamp MQTT Sensors`-integration (you might have to refresh your browser window since Home Assistant doesn't update the integration list after a reboot)
2. Set a name for the integration as well as the MQTT-prefix where updates are sent (default values are probably fine for a standard-setup but if a bridge-connection is used the MQTT-topics can be re-mapped)
3. Wait for all the devices to become present (EnergyHub, SSO's, ESOs and ESMs depending on your setup. Be patient since ESMs are only updated every 60 seconds.)

This integration will add some sensors with the prefix `<integration name>_`. For the SSO and ESO sensors, they will include the id of the SSO or ESO unit, eg `sensor.ferroamp_sso_123456_pv_string_power`.

I'm also still figuring out what some of the sensors actually are, since the Ferroamp API documentaiton still seems to be incomplete in some areas.

## Upgrading from a version before config flow was implemented

1. Remove the integration configuration. i.e this
   ```yaml
   sensor:
     - platform: ferroamp
   ```
2. Restart Home Assistant
3. Remove all Ferroamp entities (they will be re-created once the new setup is completed)
4. Follow the regular [Setup](#Setup)

_NB: Three sensors have changed name due to typos being fixed. Those three will lose their history and any usage in lovelace/automations need to be manually updated._

_Renamed sensors:_

| Old name | New name |
|----------|----------|
| sensor.ferroamp_consumtion_power | sensor.ferroamp_consumption_power |
| sensor.ferroamp_consumtion_power_reactive | sensor.ferroamp_consumption_power_reactive |
| sensor.ferroamp_interter_power_reactive | sensor.ferroamp_inverter_power_reactive |

## Update interval

To avoid too much data into home assistant, we only update sensors with new values every 30 second (average values are calculated where appropriate). This interval can be configured in the options of the integration.

## Battery control

This integration adds services for charging, discharging and autocharge. Please see Ferroamp API documentation for more info about this functionality:

If more than one EnergyHub is configured, the target parameter needs to be set to the name of the EnergyHub to control.

### ferroamp.charge
Parameter `power` needs to be specified in W.
```
power: 1000
```
### ferroamp.discharge

Parameter `power` needs to be specified in W.
```
power: 1000
```

### ferroamp.autocharge
No parameters - sets the battery back into autocharge.

## Utility meter

Inspired from this [blog post](https://www.planet4.se/home-assistant-and-solar-panel-dashboards/), I discovered the [utility meter sensor](https://www.home-assistant.io/integrations/utility_meter/) available in home assistant. I use it to track grid, solar and battery energy, hourly, daily, monthly by the configuration below in `configuration.yml`:

```
utility_meter:
  solar_energy_daily:
    source: sensor.ferroamp_total_solar_energy
    cycle: daily
  solar_energy_monthly:
    source: sensor.ferroamp_total_solar_energy
    cycle: monthly
  battery_energy_produced_daily:
    source: sensor.ferroamp_eso_20030049_total_energy_produced
    cycle: daily
  battery_energy_produced_monthly:
    source: sensor.ferroamp_eso_20030049_total_energy_produced
    cycle: monthly
  battery_energy_consumed_daily:
    source: sensor.ferroamp_eso_20030049_total_energy_consumed
    cycle: daily
  battery_energy_consumed_monthly:
    source: sensor.ferroamp_eso_20030049_total_energy_consumed
    cycle: monthly
  external_energy_consumed_daily:
    source: sensor.ferroamp_external_energy_consumed
    cycle: daily
  external_energy_consumed_monthly:
    source: sensor.ferroamp_external_energy_consumed
    cycle: monthly
  external_energy_produced_daily:
    source: sensor.ferroamp_external_energy_produced
    cycle: daily
  external_energy_produced_monthly:
    source: sensor.ferroamp_external_energy_produced
    cycle: monthly
 ```
