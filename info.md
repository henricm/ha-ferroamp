# Ferroamp MQTT Sensors
This integration adds sensors for the [Ferroamp](https://ferroamp.com) EnergyHub, SSO, ESM and ESO as well as services for controlling battery charge.

## Prerequisites
- Enable Ferroamp MQTT by contacting [Ferroamp Support](https://ferroamp.com/sv/kontakt/) to get the username and password for your Energy MQTT broker.
- Enable MQTT in Home assistant and set the broker to your Ferroamp Energy IP and configure it with your username and password received from Ferroamp (or setup a bridge-connection if you already have an MQTT-server, example for [Mosquitto here](https://selfhostedhome.com/using-two-mqtt-brokers-with-mqtt-broker-bridging/)).

## Setup
1. Add the `Ferroamp MQTT Sensors`-integration (you might have to refresh your browser window since Home Assistant doesn't update the integration list after a reboot)
2. Set a name for the integration as well as the MQTT-prefix where updates are sent (default values are probably fine for a standard-setup but if a bridge-connection is used the MQTT-topics can be re-mapped)
3. Wait for all the devices to become present (EnergyHub, SSO's, ESOs and ESMs depending on your setup. Be patient since ESMs are only updated every 60 seconds.)

## Update interval

To avoid too much data into home assistant, we only update sensors with new values every 30 second (average values are calculated where appropriate). This interval can be configured in the options of the integration.

## Battery control

This integration adds services for charging, discharging and autocharge. Please see Ferroamp API documentation for more info about this functionality.

If more than one EnergyHub is configured, the target parameter needs to be set to the name of the EnergyHub to control.
