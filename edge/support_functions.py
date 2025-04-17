import network
import socket
import time
import sensor
import ml, gc, uos
import ujson as json
from machine import LED, RTC, Pin, PWM, ADC
import ntptime


DEBUG_PRINT = True  # Set to False to disable debug prints
SEND_DATA = True

# socket globals
instrumentation_socket = 0
instrumentation_port = 0

# channel globals
server_ip = 0
command_port = 0
data_port = 0

# buzzer pin
def buzzer_init():
    buzz_pin = Pin('GPIO_EMC_08', Pin.OUT)
    pwm = PWM(buzz_pin)
    pwm.freq(2048)

# misc parameters initialisation
def init_params():
    return {
        "confidence_threshold": 0.6,
        "command_cooldown_ms": 2000,
        "last_command_time": 0
    }

def comms_setup(ssid, password):
    # Connect to WiFi
    wifi = network.WLAN(network.STA_IF)
    wifi.active(True)
    # debug_print(f'ssid:{ssid}, pws: {password}')

    # Wait until connected
    while not wifi.isconnected():
        wifi.connect(ssid, password)
        time.sleep(3)
        debug_print("Connecting ...")

    debug_print("Connected to WiFi:", wifi.ifconfig())
    led = LED("LED_BLUE")
    led.on()


def channels_setup(ip, cmd_port, d_port):
    global server_ip
    global command_port
    global data_port

    server_ip = ip
    command_port = cmd_port
    data_port = d_port

def sendCommand(command, timeout=5):
    try:
        debug_print(f"Sending to {server_ip}:{command_port} → '{command}'")
        sock = socket.socket()
        sock.settimeout(timeout)
        sock.connect((server_ip, command_port))
        sock.send(command.encode())


        # Try to receive a response (optional)
        try:
            response = sock.recv(1024)
            response_str = response.decode()
            debug_print("Got response:", response_str) # assume good
            play_good_tone()
        except:
            response_str = ""
            debug_print("No response received.")

        sock.close()
        return response_str

    except Exception as e:
        debug_print("sendCommand failed:", e)
        play_bad_tone()
        return None

def sendData(data):
    global server_ip
    global data_port
    if SEND_DATA:
        try:
            debug_print(f"Sending data to {server_ip}:{data_port} → '{data}'")
            data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data_socket.sendto(data.encode(), (server_ip, data_port))
        except Exception as e:
            debug_print("sendData failed:", e)

def init_sensor():
    sensor.reset()                         # Reset and initialize the sensor
    sensor.set_pixformat(sensor.RGB565)    # Set pixel format to RGB565 (or GRAYSCALE)
    sensor.set_framesize(sensor.QVGA)      # Set frame size to QVGA (320x240)
    sensor.set_windowing((240, 240))       # Set 240x240 window
    sensor.skip_frames(time=2000)          # Let the camera adjust
    debug_print("Sensor initialized")

def load_model_and_labels(model_path="trained.tflite", label_path="labels.txt", safety_buffer_kb=64):
    model_size = uos.stat(model_path)[6]
    mem_free_before = gc.mem_free()

    # ✅ Fixed condition: load to RAM only if it fits safely
    load_to_fb = model_size < (mem_free_before - (safety_buffer_kb * 1024))
    location = "RAM (framebuffer)" if load_to_fb else "Flash (on demand)"

    sendData("Model size: %d bytes" % model_size)
    sendData("Free RAM before load: %d bytes" % mem_free_before)
    sendData(f"Loading model into:{location}")

    net = ml.Model(model_path, load_to_fb=load_to_fb)

    gc.collect()
    mem_free_after = gc.mem_free()
    mem_used = mem_free_before - mem_free_after

    sendData("Free RAM after load: %d bytes" % mem_free_after)
    sendData("RAM used for model: %d bytes" % mem_used)
    data = "Model loaded successfully"
    sendData(data)
    debug_print(data)

    try:
        with open(label_path, "r") as f:
            labels = [line.strip() for line in f if line.strip()]
        debug_print("Loaded %d labels from %s" % (len(labels), label_path))
    except Exception as e:
        raise Exception("Failed to load labels file '%s': %s" % (label_path, e))

    return net, labels

def load_config(path="./config.json"):
    try:
        with open(path, "r") as f:
            config = json.load(f)
    except Exception as e:
        raise Exception("Failed to load config.json: " + str(e))

    required_keys = ["SSID", "PASSWORD", "SERVER_IP", "COMMANDS_PORT", "DATA_PORT"]
    for key in required_keys:
        if key not in config:
            raise Exception(f"Missing '{key}' in config.json")

    return config

def send_inference_data(data):
    debug_print(data)
    sendData(data)

def send_telemetry_data():

    telemetry_data = "Memory usage: XX, Power/Battery data: YY"
    debug_print(telemetry_data)
    sendData(telemetry_data)


def initialise_time():
    # Set NTP server to Ireland pool
    ntptime.host = '0.ie.pool.ntp.org'

    try:
        # Fetch the current time from the NTP server
        ntptime.settime()

        # Get the current time in seconds since epoch
        current_time = time.localtime()

        # Adjust for Ireland's time zone (add 1 hour for IST)
        # Note: Adjust this based on whether DST is in effect
        irish_time = time.mktime(current_time) + 3600  # 3600 seconds = 1 hour
        irish_time = time.localtime(irish_time)

        # Initialize the RTC
        rtc = RTC()
        rtc.datetime((irish_time[0], irish_time[1], irish_time[2], 0, irish_time[3], irish_time[4], irish_time[5], 0))

        print("Current time in Ireland:", rtc.datetime())
    except Exception as e:
        print(f"Failed to get time from NTP server - {e}")

        # Initialize RTC to a reasonable default time (e.g., 2025-01-01 00:00:00)
        default_time = (2025, 1, 1, 0, 0, 0, 0, 0)
        rtc = RTC()
        rtc.datetime(default_time)
        print("Initialized to default time:", rtc.datetime())



def play_tone(frequency, duration_ms):
    #pwm.freq(frequency)
    #pwm.duty_u16(32768)  # Set duty cycle to 50%
    time.sleep_ms(duration_ms)
    #pwm.duty_u16(0)      # Turn off the buzzer

def play_good_tone():
    #play_tone(1000, 200)  # 1000 Hz for 200 ms
    debug_print("play good tone")

def play_bad_tone():
    #play_tone(400, 500)   # 400 Hz for 500 ms
    debug_print("play bad tone")



# Voltage divider ratio (adjust if you're using different resistors)
TEMP_DIVIDER_RATIO = 2.0  # For example: 10kΩ + 10kΩ

def read_battery_voltage():
    adc = ADC("P6")
    raw = adc.read_u16()  # This returns an integer directly (0–4095)
    voltage = (raw / 4095.0) * 3.3  # Convert to volts at pin
    battery_voltage = voltage * TEMP_DIVIDER_RATIO  # Adjust for voltage divider
    return battery_voltage

def debug_print(*args, **kwargs):
    if DEBUG_PRINT:
        print(*args, **kwargs)
