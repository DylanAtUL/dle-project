import socket
from gtts import gTTS
import json
import os
import threading

def load_config(path="config.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}")

def speak(text):
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    os.system("mpg123 response.mp3")

def handle_gesture_commands(server_socket, command_responses):
    palm_status = False
    while True:
        print("Waiting for a connection...")
        client_socket, client_address = server_socket.accept()
        print("Connection from:", client_address)

        try:
            command = client_socket.recv(1024).decode("utf-8").strip()
            if not command:
                print("Empty command.")
                continue

            print("Received command:", command)

            if command == "Palm":
                if palm_status:
                    response = command_responses["PalmStop"]
                    palm_status = False
                else:
                    response = command_responses["Palm"]
                    palm_status = True
            else:
                response = command_responses.get(command, f"Gesture {command} not recognized.")

            print("Speaking:", response)
            speak(response)

        except Exception as e:
            print("Error handling command:", e)

        finally:
            client_socket.close()
            print("Connection closed.\n")

def handle_telemetry_data(telemetry_socket):
    while True:
        data, addr = telemetry_socket.recvfrom(1024)
        print(f"Received data from {addr}: {data.decode()}")

def run_server(config):
    host = config["host"]
    port = config["port"]
    data_port = config["data_port"]

    # Setup the socket for gesture commands
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"HAPI Server listening for Gesture commands on {host}:{port} (Ctrl+C to stop)\n")
    
    # Setup the socket for telemetry data
    telemetry_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    telemetry_socket.bind((host, data_port))
    print(f"HAPI Server listening for Telemetry data on {host}:{data_port} (Ctrl+C to stop)\n")
    
    # Define known gesture responses
    command_responses = {
        "Palm": "Hey Alexa, Play my favourite music",
        "PalmStop": "Hey Alexa, Stop the music",
        "Peace": "Hey Alexa, What time is it",
        "ThumbsUp": "Hey Alexa, Volume up",
        "ThumbsDown": "Hey Alexa, Volume down",
        "Unknown": "unknown",
    }

    # Create threads for handling gesture commands and telemetry data
    gesture_thread = threading.Thread(target=handle_gesture_commands, args=(server_socket, command_responses))
    telemetry_thread = threading.Thread(target=handle_telemetry_data, args=(telemetry_socket,))

    # Start the threads
    gesture_thread.start()
    telemetry_thread.start()

    # Wait for threads to complete
    gesture_thread.join()
    telemetry_thread.join()

if __name__ == "__main__":
    config = load_config()
    run_server(config)
