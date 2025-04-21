# this script capture audio and direct feeds it intp vosk model
# when ww detected a new recording will take place

import subprocess
import paho.mqtt.client as mqtt
import json
import vosk
import time
import io
import threading

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
mqtt_client.loop_start()

# Listen for Wake Word and Store Audio in Memory
def listen_for_wake_word():
    print("👂 Listening for wake word...")
    
    # Using 'arecord' for real-time capture of audio data
    command = ["arecord", "-D", "plughw:0,0", "-r", "16000", "-f", "S16_LE", "-c", "1", "-B", "500000", "-F", "100000"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    
    detected = False
    audio_buffer = io.BytesIO()  # Memory buffer for audio data

    while True:
        audio_data = process.stdout.read(4000)  # Read 250ms chunks
        if not audio_data:
            break
        
        # Write each chunk directly into the buffer
        audio_buffer.write(audio_data)
        
        # Process the chunk to detect wake word
        if recognizer.AcceptWaveform(audio_data):
            result = json.loads(recognizer.Result())
            print(f"🎤 Recognized: {result['text']}")
            if "wakker worden" in result["text"]:  # Wake word changed to "wakker worden"
                print("🚀 Wake word detected!")
                detected = True
                break

    return process, audio_buffer if detected else None  # Return process and buffer if detected

# Record 9 seconds of audio in memory after wake word is detected
def record_audio_in_memory(process, duration=9):
    print(f"🎤 Recording {duration} seconds of audio...")
    audio_buffer = io.BytesIO()  # Reset audio buffer for recording
    
    # Record audio for the specified duration
    start_time = time.time()
    while time.time() - start_time < duration:
        audio_data = process.stdout.read(4000)  # Read 250ms chunks
        if not audio_data:
            break
        audio_buffer.write(audio_data)

    return audio_buffer.getvalue()  # Return the audio in memory

# Handle MQTT Publishing
def mqtt_publish(audio_bytes):
    print("📡 Sending audio to MQTT...")
    mqtt_client.publish(MQTT_TOPIC, audio_bytes)
    print("✅ Audio sent!")

# Main loop (Wake Word Detection in Main Thread)
if __name__ == "__main__":
    while True:
        # Start the wake word detection
        process, audio_data = listen_for_wake_word()
        if audio_data:
            # Once the wake word is detected, record the 9 seconds of audio in memory
            print("🚀 Wake word detected, recording 9 seconds of audio...")
            recorded_audio = record_audio_in_memory(process, duration=9)
            
            if recorded_audio:
                # Publish the recorded audio directly from memory
                threading.Thread(target=mqtt_publish, args=(recorded_audio,), daemon=True).start()
            
            # Terminate the 'arecord' process after sending the audio
            process.terminate()
            
        # Optional: Reduce the delay to make the system more responsive
        time.sleep(0.1)

        # Reinitialize the 'arecord' process to continue listening
        print("🎤 Reinitializing the audio capture process...")
