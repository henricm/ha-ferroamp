# Ferroamp - Home assistant sensors for Ferroamp EnergyHub
This is still very much still work in progress, so please use this component with caution.

## Prerequisites

- Enable Ferroamp MQTT by contacting Ferroamp Support and to get the username and password for your Energy MQTT broker.
- Enable MQTT in Home assistant and set the broker to your Ferroamp Energy IP and configure it with your username and password received from Ferroamp.

### Git installation

1. Make sure you have git installed on your machine.
2. Navigate to you home assistant configuration folder.
3. Create a `custom_components` folder of it does not exist, and cd into it.
4. Execute the following command: `git clone https://github.com/henricm/ha-ferroamp.git ferroamp`

## Setup

1. Add an empty nibe configuration block to your `<config dir>/configuration.yaml`

```yaml
ferroamp:
```

There are currently no configuration options and this integration will a bunch or sensors with the prefix `ferroamp_`. For the SSO and ESO sensors, they will include the id of the SSO or ESO unit, eg `sensor.ferroamp_sso_123456_pv_string_power`. 

I'm also still figuring out what some of the sensors actually is, since the Ferroamp API documentaiton still seems to be incomplete in some areas.
