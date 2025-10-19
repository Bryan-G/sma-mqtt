import sys
import argparse
import json
import requests
import collections
import paho.mqtt.client as mqttc
import warnings

from requests.packages.urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings('ignore', category=InsecureRequestWarning)
warnings.filterwarnings('ignore', message="Callback API version 1 is deprecated")

# Magic numbers to locate measurement type
DC_POWER_OFFSET = "6380_40251E00"
DC_VOLTAGE_OFFSET = "6380_40451F00"
DC_CURRENT_OFFSET = "6380_40452100"
MEASURED_TOTAL_OFFSET = "6400_00260100"
MEASURED_DAILY_OFFSET = "6400_00262200"

# Argument parser setup
parser = argparse.ArgumentParser(description="Data collector agent for SMA SunnyBoy to MQTT")
parser.add_argument('--InvIP', required=True, help='The IP of the inverter to collect data from')
parser.add_argument('--InvPass', required=True, help='The password for the User account on the Inverter')
parser.add_argument('--MQTTIP', required=True, help='The IP of the MQTT server to publish messages to')
parser.add_argument('--MQTTTopic', required=True, help='The MQTT topic(root) to publish messages to. /<inverter-serial> will be added')
parser.add_argument('--verbose', action='store_true', help='Enable verbose output')

args = parser.parse_args()

inverter = args.InvIP
inverterUrl = 'https://' + inverter
password = args.InvPass
mqttIp = args.MQTTIP
mqttTopic = args.MQTTTopic
verbose = args.verbose

# Headers and cookies
cookies = {
    'tmhDynamicLocale.locale': 'en-us',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.5',
    'Content-Type': 'application/json;charset=utf-8',
    'Origin': inverterUrl,
    'Connection': 'keep-alive',
    'Referer': inverterUrl,
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Priority': 'u=0',
}

json_data = {
    'right': 'usr',
    'pass': password
}

# Login request 
try:
    with requests.post(inverterUrl + '/dyn/login.json', cookies=cookies, headers=headers, json=json_data, verify=False) as loginResp:
        loginResp.raise_for_status()  # Check for HTTP request errors
        loginJson = loginResp.json()    

    if "result" not in loginJson or "sid" not in loginJson["result"] or loginJson["result"]["sid"] is None:
        print(f"Unable to login to inverter webui. Response: {loginResp.text}")
        sys.exit(1)

    sid = loginJson["result"]["sid"]
    cookies["user443"] = '{"role":{"bitMask":2,"title":"usr","loginLevel":1},"username":861,"sid": "' + sid + '"}'

except requests.exceptions.RequestException as e:
    print(f"Error during login request: {e}")
    sys.exit(1)

# Get inverter data
params = {'sid': sid}
json_data = {'destDev': []}

try:
    with requests.post(inverterUrl + '/dyn/getAllOnlValues.json', params=params, cookies=cookies, headers=headers, json=json_data, verify=False) as allIValuesResp:
        allIValuesResp.raise_for_status()    
        sbData = allIValuesResp.json()

except requests.exceptions.RequestException as e:
    print(f"Error during getAllOnlValues request: {e}")
    sys.exit(1)

# Process and publish data to MQTT
for inverterSerial, value in sbData.get("result", {}).items():
    mqttJson = collections.defaultdict(dict)
    try:
        for index, val in enumerate(value.get(DC_POWER_OFFSET, {}).get("1", [])):
            tracker = "Tracker" + str(index + 1)
            mqttJson["DC Power"][tracker] = val.get("val", None)

        for index, val in enumerate(value.get(DC_VOLTAGE_OFFSET, {}).get("1", [])):
            tracker = "Tracker" + str(index + 1)
            mqttJson["DC Voltage"][tracker] = val.get("val", None)

        for index, val in enumerate(value.get(DC_CURRENT_OFFSET, {}).get("1", [])):
            tracker = "Tracker" + str(index + 1)
            mqttJson["DC Current"][tracker] = val.get("val", None)

        mqttJson["Total Yield"] = value.get(MEASURED_TOTAL_OFFSET, {}).get("1", [{}])[0].get("val", None)
        mqttJson["Daily Yield"] = value.get(MEASURED_DAILY_OFFSET, {}).get("1", [{}])[0].get("val", None)
        mqttJson["Inverter"] = inverterSerial

        if verbose:
            print(json.dumps(mqttJson))

        # MQTT client connection and publishing
        client = mqttc.Client(mqttc.CallbackAPIVersion.VERSION1,"inverter")
        try:
            client.connect(mqttIp, 1883, 60)
            client.publish(mqttTopic + "/" + inverterSerial, json.dumps(mqttJson))

        except Exception as e:
            print(f"Error connecting to MQTT server or publishing message: {e}")
            continue

    except KeyError as e:
        print(f"Missing data for {inverterSerial}: {e}")
        continue

# Logout from the inverter
try:
    with requests.post(inverterUrl + '/dyn/logout.json?sid=' + sid, params=params, cookies=cookies, headers=headers, json=json_data, verify=False) as resp:
        resp.raise_for_status()

except requests.exceptions.RequestException as e:
    print(f"Error during logout request: {e}")
    sys.exit(1)

