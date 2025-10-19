import json
import argparse
import paho.mqtt.client as mqtt

# ----------------------------
# Unit mappings by top-level key
# ----------------------------
UNIT_MAP = {
    "DC Power": "W",
    "DC Voltage": "mV",
    "DC Current": "mA",
    "Total Yield": "Wh",
    "Daily Yield": "Wh",
    "Temperature": "°F",  # Add more as needed
    "Humidity": "%",
    "AQI": "µg/m³"
}

# ----------------------------
# Flatten JSON: return list of (key path list, value)
# ----------------------------
def flatten_json(data, path=None):
    if path is None:
        path = []
    sensors = []

    if isinstance(data, dict):
        for k, v in data.items():
            sensors += flatten_json(v, path + [k])
    else:
        sensors.append((path, data))
    return sensors

# ----------------------------
# Build MQTT Discovery Payload
# ----------------------------
def build_discovery_payload(base_topic, key_path, device_id):
    name = " ".join(key_path).title()
    object_id = "_".join(k.replace(" ", "_").replace(".", "_").lower() for k in key_path)
    top_key = key_path[-1] if len(key_path) > 0 else "unknown"

    # Safely build value_template
    value_template = "{{ value_json" + "".join([f"[{json.dumps(k)}]" for k in key_path]) + " | round(2) }}"

    payload = {
        "name": name,
        "state_topic": base_topic,
        "value_template": value_template,
        "unique_id": f"{device_id}_{object_id}",
        "object_id": object_id,
        "device": {
            "identifiers": [device_id],
            "name": f"{device_id}",
        }
    }

    # Add unit if known
    if top_key in UNIT_MAP:
        payload["unit_of_measurement"] = UNIT_MAP[top_key]

    return payload

# ----------------------------
# Print or publish discovery configs
# ----------------------------
def publish_discovery_configs(client, topic, payload, debug=False):
    device_id = topic.split('/')[-1]
    flat_keys = flatten_json(payload)

    print("\n🔍 Flattened keys:", flat_keys)  # Diagnostic print

    for key_path, _ in flat_keys:
        config_payload = build_discovery_payload(topic, key_path, device_id)
        object_id = config_payload["object_id"]
        discovery_topic = f"homeassistant/sensor/{device_id}/{object_id}/config"

        if debug:
            print(f"\n📦 Discovery topic: {discovery_topic}")
            print(json.dumps(config_payload, indent=2))
        else:
            client.publish(discovery_topic, json.dumps(config_payload), retain=True)
            print(f"✅ Published discovery config to: {discovery_topic}")

# ----------------------------
# MQTT callbacks
# ----------------------------
def on_connect(client, userdata, flags, rc):
    print(f"✅ Connected to MQTT broker (rc={rc})")
    client.subscribe(userdata["topic"])
    print(f"📡 Subscribed to topic: {userdata['topic']}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
    except json.JSONDecodeError:
        print("❌ Invalid JSON payload received.")
        return

    print("📥 Full payload:")
    print(json.dumps(payload, indent=2))

    print("🔄 Received valid JSON. Generating discovery configs...")
    publish_discovery_configs(client, msg.topic, payload, debug=userdata["debug"])

    # Exit after one message
    client.loop_stop()
    client.disconnect()
    print("✅ Discovery config generation complete. Exiting.")

# ----------------------------
# Main
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="MQTT → Home Assistant Discovery Config Generator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address (default: localhost)")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--topic", required=True, help="MQTT topic to subscribe to")
    parser.add_argument("--client-id", default="mqtt_to_discovery", help="MQTT client ID")
    parser.add_argument("--debug", action="store_true", help="Print discovery configs instead of publishing")

    args = parser.parse_args()

    client = mqtt.Client(client_id=args.client_id, userdata={"topic": args.topic, "debug": args.debug})
    client.on_connect = on_connect
    client.on_message = on_message

    print("🔌 Connecting to broker...")
    try:
        client.connect(args.broker, args.port, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ MQTT connection failed: {e}")

if __name__ == "__main__":
    main()

