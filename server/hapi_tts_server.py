import socket
import pyttsx3
import json

def load_config(path="config.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load config: {e}")

def init_tts(rate, volume):
    engine = pyttsx3.init()
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)
    return engine

def run_server(config):
    host = config["host"]
    port = config["port"]

    engine = init_tts(config["speech_rate"], config["speech_volume"])

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"HAPI Server listening on {host}:{port} (Ctrl+C to stop)\n")

    # Optional: define known gesture responses
    command_responses = {
        "call me": "You did the Call Me gesture.",
        "palm": "You showed your palm.",
        "peace": "Peace sign detected.",
        "thumbs up": "Thumbs up! Great job.",
        "thumbs down": "Thumbs down received.",
        "yes": "yes its working",
        "no" : "no is working too",
        "ThumbsUp": "Thumbs up! Great job.",
        "ThumbsDown": "Thumbs down received.",
        "Unknown": "unknown",
    }

    try:
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

                response = command_responses.get(command, f"Gesture {command} not recognized.")
                print("Speaking:", response)
                engine.say(response)
                engine.runAndWait()

            except Exception as e:
                print("Error handling command:", e)

            finally:
                client_socket.close()
                print("Connection closed.\n")

    except KeyboardInterrupt:
        print("\nExiting server.")

    finally:
        server_socket.close()

if __name__ == "__main__":
    config = load_config()
    run_server(config)
