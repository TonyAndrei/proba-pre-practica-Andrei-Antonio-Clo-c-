import random
import time
import json
import os
import threading
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import paho.mqtt.client as mqtt
from web3 import Web3

# === CONFIG ===
BOT_TOKEN = "7781626526:AAGoAunJeu641KP1p65kDwwhVX-632sgkZw"   # << Înlocuiești cu tokenul tău real!
MQTT_BROKER = "mqtt.beia-telemetrie.ro"
MQTT_PORT = 1883
MQTT_TOPIC = "training/device/tony"
USERNAME = "tony"

GANACHE_URL = "http://127.0.0.1:7545"
ACCOUNT = "0xE002d91aecD7311Fcb1Fa2876B012C5559D7C47D"
PRIVATE_KEY = "0x0f05b48e5808586e6de9e1750d6337bb81a3a414be56d1e5858e2b53ba3dbf66"
TO_ADDRESS = "0x49b83C6A3b7b7683688c78150325F06F27e62684"

LOCAL_FOLDER = "./tony_backup"
BACKUP_FILE = f"{LOCAL_FOLDER}/backup.json"

# === Variabilă globală cu ultima citire ===
latest_data = {"message": "No motor data yet."}

# === Asigură folder backup ===
os.makedirs(LOCAL_FOLDER, exist_ok=True)

# === Blockchain setup ===
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))
print("Blockchain connected:", web3.is_connected())

# === MQTT CALLBACKS ===
def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global latest_data
    try:
        payload = json.loads(msg.payload.decode())
        latest_data = {
            "message": (
                f"🛠️ Motor Speed: {payload['motor_speed_rpm']} rpm\n"
                f"🌡️ Temperature: {payload['motor_temperature_c']} °C\n"
                f"⏱️ Time: {payload['timestamp']}"
            ),
            "raw": payload
        }
        print("Received MQTT:", latest_data["message"])
    except Exception as e:
        print("Error parsing MQTT message:", e)

# === Start MQTT Publisher ===
def generate_motor_data():
    client_pub = mqtt.Client(client_id="motor_publisher", protocol=mqtt.MQTTv311)
    client_pub.connect(MQTT_BROKER, MQTT_PORT)

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

        client_pub.publish(MQTT_TOPIC, json.dumps(data))
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
                'to': TO_ADDRESS,
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

# === Start MQTT Receiver ===
def start_mqtt_receiver():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER)
    client.loop_forever()

# === Telegram Handlers ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hello! Use /latest to get the latest motor data.")

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(latest_data["message"])

# === Main ===
def main():
    # Start MQTT publisher thread
    threading.Thread(target=generate_motor_data, daemon=True).start()

    # Start MQTT receiver thread
    threading.Thread(target=start_mqtt_receiver, daemon=True).start()

    # Start Telegram bot
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("latest", latest))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()