# Edge Impulse - OpenMV Image Classification Example
#
# This work is licensed under the MIT license.
# Copyright (c) 2013-2024 OpenMV LLC. All rights reserved.
# https://github.com/openmv/openmv/blob/master/LICENSE

import sensor, time

# import for project functions
from support_functions import comms_connect, sendCommand, init_sensor, load_model_and_labels, init_params, load_config


# parameters initialisation
params = init_params()
confidence_threshold = params["confidence_threshold"]
command_cooldown_ms = params["command_cooldown_ms"]
last_command_time = params["last_command_time"]

# comms setup
config = load_config() # Load comms config from a config.json file
comms_connect(config["SSID"], config["PASSWORD"]) # Connect using WiFi credentials
server_ip = config["SERVER_IP"] # Point connection to server
server_port = config["SERVER_PORT"]

# sensor initialisation
init_sensor()

# load model
net, labels = load_model_and_labels("trained.tflite", "labels.txt")
time.sleep(1)

# instrumentation init
clock = time.clock()

while True:
    # capture image
    clock.tick()
    img = sensor.snapshot()

    # Measure inference time
    t_start = time.ticks_us()
    predictions = net.predict([img])[0].flatten().tolist()
    t_end = time.ticks_us()
    inference_time_ms = time.ticks_diff(t_end, t_start) / 1000  # convert to ms

    # determine propabilities, only send if above a confidence threshold and if not throttling
    predictions_list = list(zip(labels, predictions))
    for label, score in predictions_list:
        print("%s = %f" % (label, score))
        if score > confidence_threshold:
            now = time.ticks_ms()
            if time.ticks_diff(now, last_command_time) > command_cooldown_ms:
                print(f"Sending command for: {label} ({score:.2f})")
                resp = sendCommand(server_ip, f"{label}", port=server_port)
                print("Response:", resp)
                last_command_time = now
            else:
                print("Throttled: not sending again yet")

    # print important instrmentation details
    print("Inference time: %.2f ms" % inference_time_ms, "FPS:", clock.fps())
    # let other things get a chance
    time.sleep_ms(10)

# note - removing predictions and label probabilities ie if loop does nothing,
# gives and FPS of 46.5

