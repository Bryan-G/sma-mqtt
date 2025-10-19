AI generated scripts to add keys from a json payload to Home Assistant. 

The scripts subscribe to the mqtt topic and then generate the yaml or publishes the discovery topic.

Use --debug with mqtt_to_ha_discovery.py to see the sensors to be added to Home Assistant.


Examples:
python3 ha_yaml_generator.py --broker 192.168.1.250 --port 1883 --topic solartest/power/<inverter>
python3 mqtt_to_ha_discovery.py --broker 192.168.1.250 --topic solartest/power/<inverter>

