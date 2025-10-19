Simple MQTT data collector for SMA inverters.  Tested only on the Sunnyboy 6.0us.  It runs as "user", but can be changed to custom user if needed. I pulled the values I wanted from the webui and hard coded them. I don't know if they change from model to model, or even between fw versions.  

Here is an example payload:
solartest/power/<inverter-number> {"DC Power": {"Tracker1": 0, "Tracker2": 0, "Tracker3": 0}, "DC Voltage": {"Tracker1": 0, "Tracker2": 0, "Tracker3": 0}, "DC Current": {"Tracker1": 0, "Tracker2": 0, "Tracker3": 0}, "Total Yield": 999999999, "Daily Yield": 99999, "Inverter": "<inverter-number>"}


I also have included a Dockerfile to run this in a docker container. This should eliminate issues with the python environment. It's small enough, that I just have a cronjob that kicks off the docker every minute for each of my inverters.

Example build:
docker build -t sma-mqtt .

Example run:
* * * * * docker run --rm sma-mqtt --InvIP 192.168.1.251 --InvPass <password> --MQTTIP 192.168.1.250 --MQTTTopic solartest/power
* * * * * docker run --rm sma-mqtt --InvIP 192.168.1.252 --InvPass <password> --MQTTIP 192.168.1.250 --MQTTTopic solartest/power
