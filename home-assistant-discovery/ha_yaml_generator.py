import json
import yaml
import argparse
import paho.mqtt.client as mqtt

# ----------------------------
# Helper: Flatten nested JSON
# ----------------------------
def flatten_json(prefix, data):
    sensors = []
    if isinstance(data, dict):
        for k, v in data.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            sensors += flatten_json(new_prefix, v)
    else:
        sensors.append((prefix, data))
    return sensors

# ----------------------------
# Build MQTT sensor entry
# ----------------------------
def build_sensor_yaml(topic, full_key_path):
    # Use dotted path as name and friendly_name
    name = full_key_path.replace('.', ' ').title()
    value_template = "{{ value_json" + ''.join([f"[{json.dumps(k)}]" for k in full_key_path.split('.')]) + " }}"
    
    return {
        "name": name,
        "state_topic": topic,
        #"friendly_name": f'"{name}"',
        "value_template": value_template
    }

# ----------------------------
# Create full YAML from payload
# ----------------------------
def generate_ha_yaml(topic, json_payload):
    flat_keys = flatten_json("", json_payload)
    sensors = [build_sensor_yaml(topic, key) for key, _ in flat_keys]
    return yaml.dump({"mqtt": {"sensor": sensors}}, sort_keys=False, default_flow_style=False)

# ----------------------------
# MQTT Callbacks
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

    yaml_output = generate_ha_yaml(msg.topic, payload)

    print("\n--- ✅ Home Assistant YAML Output ---")
    print(yaml_output)
    print("-------------------------------------\n")

    # Stop after one message
    client.loop_stop()
    client.disconnect()

# ----------------------------
# Main function with argparse
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="MQTT to Home Assistant YAML generator (for paho-mqtt < 2.0).")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address (default: localhost)")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--topic", required=True, help="MQTT topic to subscribe to")
    parser.add_argument("--client-id", default="mqtt_to_yaml", help="MQTT client ID")

    args = parser.parse_args()

    client = mqtt.Client(client_id=args.client_id, userdata={"topic": args.topic})
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        print("🔌 Connecting to broker...")
        client.connect(args.broker, args.port, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ Connection error: {e}")

if __name__ == "__main__":
    main()

