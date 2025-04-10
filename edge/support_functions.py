import network
import socket
import time
import sensor
import ml, gc, uos
import ujson as json


def init_params():
    return {
        "confidence_threshold": 0.8,
        "command_cooldown_ms": 2000,
        "last_command_time": 0
    }

def comms_connect(ssid, password):
    # Connect to WiFi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    # print(f'ssid:{ssid}, pws: {password}')
    wifi.connect(ssid, password)

    # Wait until connected
    while not wifi.isconnected():
        print("Connecting...rety")
        time.sleep(3)

    print("Connected to WiFi:", wifi.ifconfig())


def sendCommand(ip, command, port=80, timeout=5):
    try:
        print(f"Sending to {ip}:{port} → '{command}'")
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.send(command.encode())

        # Try to receive a response (optional)
        try:
            response = sock.recv(1024)
            response_str = response.decode()
            print("Got response:", response_str)
        except:
            response_str = ""
            print("No response received.")

        sock.close()
        return response_str

    except Exception as e:
        print("sendCommand failed:", e)
        return None


def init_sensor():
    sensor.reset()                         # Reset and initialize the sensor
    sensor.set_pixformat(sensor.RGB565)    # Set pixel format to RGB565 (or GRAYSCALE)
    sensor.set_framesize(sensor.QVGA)      # Set frame size to QVGA (320x240)
    sensor.set_windowing((240, 240))       # Set 240x240 window
    sensor.skip_frames(time=2000)          # Let the camera adjust
    print("Sensor initialized")


def load_model_and_labels(model_path="trained.tflite", label_path="labels.txt", safety_buffer_kb=64):
    model_size = uos.stat(model_path)[6]
    mem_free_before = gc.mem_free()

    # Fixed condition: load to RAM only if it fits safely
    load_to_fb = model_size < (mem_free_before - (safety_buffer_kb * 1024))
    location = "RAM (framebuffer)" if load_to_fb else "Flash (on demand)"

    print("Model size: %d bytes" % model_size)
    print("Free RAM before load: %d bytes" % mem_free_before)
    print("Loading model into:", location)

    net = ml.Model(model_path, load_to_fb=load_to_fb)

    gc.collect()
    mem_free_after = gc.mem_free()
    mem_used = mem_free_before - mem_free_after

    print("Free RAM after load: %d bytes" % mem_free_after)
    print("RAM used for model: %d bytes" % mem_used)
    print("Model loaded successfully\n")

    try:
        with open(label_path, "r") as f:
            labels = [line.strip() for line in f if line.strip()]
        print("Loaded %d labels from %s" % (len(labels), label_path))
    except Exception as e:
        raise Exception("Failed to load labels file '%s': %s" % (label_path, e))

    return net, labels


def load_config(path="./config.json"):
    try:
        with open(path, "r") as f:
            config = json.load(f)
    except Exception as e:
        raise Exception("Failed to load config.json: " + str(e))

    required_keys = ["SSID", "PASSWORD", "SERVER_IP", "SERVER_PORT"]
    for key in required_keys:
        if key not in config:
            raise Exception(f"Missing '{key}' in config.json")

    return config

