import random
import time
import json
import os
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from web3 import Web3

# --- CONFIG ---
MQTT_BROKER = "mqtt.beia-telemetrie.ro"
MQTT_PORT = 1883
MQTT_TOPIC = "training/device/tony"
USERNAME = "tony"

GANACHE_URL = "http://127.0.0.1:7545"
ACCOUNT = "0xE002d91aecD7311Fcb1Fa2876B012C5559D7C47D"   # expeditor
PRIVATE_KEY = "0x0f05b48e5808586e6de9e1750d6337bb81a3a414be56d1e5858e2b53ba3dbf66"   # cheia privată a contului

TO_ADDRESS = "0x49b83C6A3b7b7683688c78150325F06F27e62684"   # destinatar

LOCAL_FOLDER = "./tony_backup"
BACKUP_FILE = f"{LOCAL_FOLDER}/backup.json"

# Asigură folder backup
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# MQTT setup
client = mqtt.Client(client_id="motor_publisher", protocol=mqtt.MQTTv311)
client.connect(MQTT_BROKER, MQTT_PORT)

# Blockchain setup
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
print("Blockchain connected:", web3.is_connected())

# --- Function ---
def generate_motor_data():
    while True:
        motor_speed = random.randint(0, 8000)
        base_temp = 0.015 * motor_speed
        motor_temp = round(base_temp + random.uniform(-5.0, 5.0), 2)
        timestamp = datetime.now(timezone.utc).isoformat()

        data = {
            "motor_speed_rpm": motor_speed,
            "motor_temperature_c": motor_temp,
            "timestamp": timestamp
        }

        # MQTT
        client.publish(MQTT_TOPIC, json.dumps(data))
        print(f"Published to MQTT: {data}")

        # Local backup
        with open(BACKUP_FILE, "a") as f:
            f.write(json.dumps(data) + "\n")
            print("Saved to local backup.")

        # Blockchain TX
        try:
            nonce = web3.eth.get_transaction_count(ACCOUNT)

            tx = {
                'nonce': nonce,
                'to': TO_ADDRESS,  # Destinatarul real!
                'value': 0,
                'gas': 2000000,
                'gasPrice': web3.to_wei('50', 'gwei'),
                'data': web3.to_hex(text=json.dumps(data))
            }

            signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print("Sent to Blockchain. Tx hash:", web3.to_hex(tx_hash))

        except Exception as e:
            print(f"Blockchain error: {e}")

        time.sleep(5)

# --- Main ---
if __name__ == "__main__":
    generate_motor_data()
