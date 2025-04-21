import subprocess
import paho.mqtt.client as mqtt
import os
import wave
import numpy as np
from vosk import Model, KaldiRecognizer
import sys
import time

# MQTT Configuration
mqtt_broker = "192.168.1.200"  # Example broker, replace with OVOS broker info
mqtt_port = 1883
mqtt_topic = "ovos/audio"
mqtt_client_id = "microphone-client"

# Initialize MQTT Client
#client = mqtt.Client(mqtt_client_id)
client = mqtt.Client(client_id="audio_sat", protocol=mqtt.MQTTv5) 
client.connect(mqtt_broker, mqtt_port, 60)

# Load Vosk model for speech recognition
VOSK_MODEL_PATH = "/home/ovos/audio_sat/model"  # Adjust this path 
model = Model(VOSK_MODEL_PATH)  # Load your Vosk model (replace 'model' with your actual path)
recognizer = KaldiRecognizer(model, 16000)

# Set up audio recording command
recording_duration = 9  # seconds

def record_audio(duration):
    # Record audio from microphone using `arecord` and save it as raw WAV data
    cmd = ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", "16000", "-t", "wav", "-d", str(duration), "-c", "1", "temp.wav"]
    subprocess.run(cmd)
    with wave.open("temp.wav", "rb") as wf:
        # Read audio data as bytearray
        audio_data = wf.readframes(wf.getnframes())
    return audio_data

def detect_wake_word(audio_data):
    # Feed audio data to Vosk for recognition
    if recognizer.AcceptWaveform(audio_data):
        result = recognizer.Result()
        print(result)  # Output the result for debugging
        return result
    return None

def send_audio_data_via_mqtt(audio_data):
    # Send the bytearray via MQTT
    client.publish(mqtt_topic, audio_data)

def process_audio():
    print("Listening for wake word...")
    while True:
        # Capture audio from microphone in 1-second chunks for real-time processing
        audio_data = record_audio(1)
        
        # Detect wake word
        result = detect_wake_word(audio_data)
        
        if result and "wakeword" in result.lower():  # Assuming "wakeword" is part of the result
            print("Wake word detected! Capturing 9 seconds of audio...")
            
            # Capture 9 seconds of audio after wake word detection
            audio_data = record_audio(recording_duration)
            
            # Send the 9 seconds audio data to OVOS via MQTT
            send_audio_data_via_mqtt(audio_data)
            print("Audio sent to OVOS.")
        
        time.sleep(0.5)

if __name__ == "__main__":
    try:
        process_audio()
    except KeyboardInterrupt:
        print("Exiting...")
        os.remove("temp.wav")  # Clean up temporary file
