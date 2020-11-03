# Home assistant sensors for Ferroamp EnergyHub
This is still very much still work in progress, so please use this component with caution.

Ferroamp MQTT support sends updates to these topics:

 * extapi/data/ehub (interval 1s)
 * extapi/data/eso (interval 5s)
 * extapi/data/sso (interval 5s)
 * extapi/data/esm (interval 60s)
 
## Prerequisites
- Home assistant `0.115.0`
- Enable Ferroamp MQTT by contacting Ferroamp Support and to get the username and password for your Energy MQTT broker.
- Enable MQTT in Home assistant and set the broker to your Ferroamp Energy IP and configure it with your username and password received from Ferroamp.

### Git installation

1. Make sure you have git installed on your machine.
2. Navigate to you home assistant configuration folder.
3. Create a `custom_components` folder of it does not exist, and cd into it.
4. Execute the following command: `git clone https://github.com/henricm/ha-ferroamp.git ferroamp`

## Setup

1. Add a sensor for the ferroamp platform to your `<config dir>/configuration.yaml`

```yaml
sensor:
  - platform: ferroamp
```

There are currently no configuration options. This integration will add some sensors with the prefix `ferroamp_`. For the SSO and ESO sensors, they will include the id of the SSO or ESO unit, eg `sensor.ferroamp_sso_123456_pv_string_power`. 

I'm also still figuring out what some of the sensors actually are, since the Ferroamp API documentaiton still seems to be incomplete in some areas.

## Update interval

To avoid too much data into home assistant, we check the timestamp sent by Ferroamp to make sure we only update sensors with new values every 30 second. This interval I expect to be configurable later on.

## Battery control

This integration adds services for charging, discharging and autocharge. Please see Ferroamp API documentation for more info about this functionality:

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
 
 ## Known issues

I haven't figured out how to check if an entity already exists in home assistant so after first startup you'll see error logging when sensors are added when they already exits:
```
Entity id already exists - ignoring: sensor.ferroamp_sso_pv_string_power
```

