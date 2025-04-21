# this script uses asound instead of sounddevice library

import subprocess
import paho.mqtt.client as mqtt
import json
import vosk
import wave
import time
import os

# MQTT Configuration
MQTT_BROKER = "192.168.1.200"  # Change this to your broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "ovos/audio"

# Wake Word Model (Download from Vosk if needed)
VOSK_MODEL_PATH = "/home/ovos/audio_sat/model"  # Adjust this path

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
#mqtt_client.loop_start()

# Record 9 seconds of audio after wake word
def record_audio(filename, duration=9):
    print(f"🎤 Recording {duration} seconds of audio...")
    command = ["nice", "-n", "-10", "arecord", "-D", "plughw:0,0", "-r", "16000", "-f", "S16_LE", "-B", "500000", "-F", "50000", "-c", "1", "-d", str(duration), filename]
    subprocess.run(command)
    print("🎙️ Recording complete.")

# Convert Audio to Byte Array
def audio_to_bytearray(filename):
    with open(filename, "rb") as f:
        return f.read()

# Listen for Wake Word
def listen_for_wake_word():
    print("👂 Listening for wake word...")
    # "nice", "-n", "-10", is used to set process priority -B and-F added to reduce overrun
    command = ["nice", "-n", "-10", "arecord", "-D", "plughw:0,0", "-r", "16000", "-f", "S16_LE", "-B", "500000", "-F", "50000", "-c", "1"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)

    while True:
        audio_data = process.stdout.read(2000) #4000)  # Read 250ms chunks
        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            print(f"🎤 Recognized: {result['text']}")

            if "wakeword" in result["text"]:  # Replace with your wake word
                print("🚀 Wake word detected!")
                process.terminate()  # Stop listening
                return True

# Main Loop
while True:
    if listen_for_wake_word():
        audio_filename = "wakeword_audio.wav"
        record_audio(audio_filename)

        # Convert audio to byte array
        audio_bytes = audio_to_bytearray(audio_filename)

        # Publish to MQTT
        print("📡 Sending audio to MQTT...")
        mqtt_client.publish(MQTT_TOPIC, audio_bytes)
        print("✅ Audio sent!")

        # Optional: Delete audio file after sending
        os.remove(audio_filename)

    # Add small delay to prevent CPU overload
    time.sleep(0.5)
