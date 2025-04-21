# this script uses memory instead of the SDcard read and write files

import threading
import subprocess
import paho.mqtt.client as mqtt
import json
import vosk
import time
import os
import io

# MQTT Configuration
MQTT_BROKER = "192.168.1.200"  # Change this to your broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "ovos/audio"

# Wake Word Model (Download from Vosk if needed)
VOSK_MODEL_PATH = "/home/ovos/audio_sat/model2"  # Adjust this path

# Initialize Vosk Wake Word Model
model = vosk.Model(VOSK_MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, 16000)

# MQTT Client Setup
mqtt_client = mqtt.Client(client_id="audio_sat", protocol=mqtt.MQTTv5)

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("✅ Connected to MQTT Broker!")
    else:
        print(f"⚠️ Connection failed with status code {rc}")

mqtt_client.on_connect = on_connect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

# Listen for Wake Word and Store Audio in Memory
def listen_for_wake_word():
    print("👂 Listening for wake word...")
    command = ["arecord", "-D", "plughw:0,0", "-r", "16000", "-f", "S16_LE", "-c", "1", "-B", "500000", "-F", "100000"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    audio_buffer = io.BytesIO()
    detected = False

    while True:
        audio_data = process.stdout.read(4000)  # Read 250ms chunks
        if not audio_data:
            break
        audio_buffer.write(audio_data)

        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            print(f"🎤 Recognized: {result['text']}")
            if "wakeword" in result["text"]:  # Replace with your wake word
                print("🚀 Wake word detected!")
                detected = True
                break

    process.terminate()
    return audio_buffer.getvalue() if detected else None  # Ensure a valid return

# Handle MQTT Publishing
def mqtt_publish(audio_bytes):
    print("📡 Sending audio to MQTT...")
    mqtt_client.publish(MQTT_TOPIC, audio_bytes)
    print("✅ Audio sent!")

# Main loop (Wake Word Detection in Main Thread)
if __name__ == "__main__":
    while True:
        audio_data = listen_for_wake_word()
        if audio_data:
            threading.Thread(target=mqtt_publish, args=(audio_data,), daemon=True).start()
        time.sleep(0.1)  # Reduced delay to prioritize wake word detection