# main.py

# application related
from flask import Flask, render_template, Response, request, make_response

from datetime import timedelta, date
import json

# Models
from models.detection import Detection
from models.inspection import InspectionReport

# AI related
import numpy as np
import os
from camera_drivers.realsense.RealSense435i import RealSense435i as depth_cam
from camera_drivers.ricoh_theta.thetav import RicohTheta as ricoh_camera
from detectors.yolo_detector.yolo import Yolo
from detectors.mask_rcnn.mrcnn import MRCNN
import cv2
import time

# might not be neede
from camera import VideoCamera

import platform
# Uncomment on nano to import GPIO modules

# setup illumination on nano
use_gpio = False
if str(platform.platform()).__contains__("Windows"):
    print("On windows, not importing GPIO")
    use_gpio = False
else:
    import RPi.GPIO as GPIO
    use_gpio = True

    # Pin Definitions
    output_pin = 23  # BCM pin 23, BOARD pin 16
    output_pin2 = 27  # BCM 27, board 13
    output_pin3 = 18  # BCN 18, board 12
    # Uncomment on nano to init gpio pins...
    GPIO.setmode(GPIO.BCM)  # BCM pin-numbering scheme from Raspberry Pi
    # # set pin as an output pin with optional initial state of LOW
    GPIO.setup(output_pin, GPIO.OUT, initial=GPIO.LOW)
    # GPIO.setup(output_pin2, GPIO.OUT, initial=GPIO.LOW)
    # GPIO.setup(output_pin3, GPIO.OUT, initial=GPIO.LOW)
    # Ilumination
illumination_on = False

illumination = "OFF"


# Application
app = Flask(__name__)


# Ricoh credentials
cameraName = None
cameraPassword = None
ricoh = None
ricoh_state = "Not connected"
# detector flags
enable_detection = "OFF"
detector = None

# depth camera params
# TODO make the streams selectable from setting
realsense_enabled = False
enable_rgb = True
enable_depth = True
enable_imu = False
device_id = None
width = 1280
height = 720
channels = 3

# variable to hold travel distance
distance = 0.00
# variable to hold realsense camera obj
camera = None

# List to contain the detections from inspection
detections_results = []
# inspection report
inspection_report = None

# Timer
start_time = None
current_time = start_time
elapsed_time = None


# Main page
@ app.route('/')
def index():
    global realsense_enabled
    return render_template('index.html', cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection)


# Navigate to inspection page
@ app.route('/inspection/')
def render_camera_view():
    global realsense_enabled, detections_results, elapsed_time, distance, inspection_report
    return render_template('inspection_screen.html', travel_distance=distance, the_inspection_time=elapsed_time, ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection, detections=detections_results, report_details=inspection_report)

# Navigate to ricoh page


@ app.route('/ricoh/')
def render_ricoh_view():
    global ricoh, ricoh_state, cameraName, cameraPassword
    return render_template('ricoh_screen.html', travel_distance=distance, the_inspection_time=elapsed_time, ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection, detections=detections_results, report_details=inspection_report)


# Navigate to settingds
@ app.route('/settings/')
def render_settings_view():
    global realsense_enabled, cameraName, cameraPassword
    return render_template('settings_screen.html', ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection)


# Turn illumination on
@ app.route("/illumination_on/", methods=['POST'])
def illumination_on():
    # uncomment on nano
    global output_pin, curr_value, illumination
    if use_gpio:
        curr_value = GPIO.HIGH
        GPIO.output(output_pin, curr_value)
    illumination = "ON"
    return render_camera_view()


# Turn illumination off
@ app.route("/illumination_off/", methods=['POST'])
def illumination_off():
    # uncomment on nano
    global output_pin, curr_value, illumination
    if use_gpio:
        curr_value = GPIO.LOW
        GPIO.output(output_pin, curr_value)

    illumination = "OFF"
    return render_camera_view()


# Turn depth camera on
# TODO add exception handling , returning appropriate response...
@ app.route("/realsense_on/", methods=['POST'])
def start_realsense_camera():
    global realsense_enabled, camera
    print(realsense_enabled)
    if not realsense_enabled:
        realsense_enabled = True

    camera = depth_cam(width=width, height=height, channels=channels,
                       enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)
    return render_settings_view()

# Turn depth cam off
# TODO add exception handling , returning appropriate response...


@ app.route("/realsense_off/", methods=['POST'])
def stop_realsense_camera():
    global realsense_enabled, camera
    if realsense_enabled:
        realsense_enabled = False
        camera.shutdown()
    else:
        print("Camera is not running...")
    return render_settings_view()

# Load yolo detector
# TODO add exception handling , returning appropriate response...


@ app.route("/enable_detector_yolo/", methods=['POST'])
def enable_detector_yolo():
    global enable_detection, detector
    if not enable_detection:
        enable_detection = True

    detector = Yolo(confidence_param=0.3, thresh_param=0.5)
    if detector is not None:
        enable_detection = "Yolo detector"
    return render_settings_view()

# Load mask rcnn detector
# TODO add exception handling , returning appropriate response...


@ app.route("/enable_detector_mrcnn/", methods=['POST'])
def enable_detector_mrcnn():
    global enable_detection, detector

    detector = MRCNN(use_cuda=True)

    if detector is not None:
        enable_detection = "Mask RCNN"

    return render_settings_view()

# Disable detector
# TODO add exception handling , returning appropriate response...


@ app.route("/disable_detector/", methods=['POST'])
def disable_detector():
    global enable_detection

    detector = None

    if detector is None:
        print("Detector stopped...")
        enable_detection = "OFF"

    return render_settings_view()

# Writes the inspection report data to json file.
# TODO add time to inspection report name ...


@ app.route("/new_report/", methods=['POST'])
def new_report():
    global inspection_report, detections_results, start_time

    inspection_report.addDetections(detections_results)

    inspection_report.write_inspection_file(date.today().strftime("%d_%m_%Y"))
    # Clear report variables..
    inspection_report = None
    detections_results = []

    return render_camera_view()

# Creates inspection report object based on the input form data


@ app.route("/create_report/", methods=['POST'])
def create_report():
    global inspection_report
    operator_name = request.form['inspectorName']
    inspection_date = request.form['datepicker']
    city = request.form['city']
    street = request.form['street']
    pipe_id = request.form['pipe_id']
    manhole_id = request.form['manhole_id']
    dimensions = request.form['sizes']
    shape = request.form['shapes']
    material = request.form['materials']

    inspection_report = InspectionReport(
        operator_name, inspection_date, city, street, pipe_id, manhole_id, dimensions, shape, material)
    # print(inspection_report.toJSON())
    return render_camera_view()


# Stop theta video capture
# Connects to device wifi # TODO check how this works...
# Sends the stop capture command
# Requires to have ricoh object set
@ app.route("/stop/", methods=['POST'])
def stop_capture():
    global ricoh, start_time, elapsed_time
    os.system(
        "nmcli d wifi connect {} password {} iface {}"
        .format("THETAYL00160236.OSC", "00160236", "wlp8s0"))

    elapsed_time = time.time() - start_time
    start_time = None
    if ricoh:
        response_stop = ricoh.stop_capture(withDownload=False)
    else:
        print("Ricoh device not active")

    return render_camera_view()

# Starts capture on ricoh device
# Continuous images/ or video depending on device mode


@ app.route("/start/", methods=['POST'])
def start_capture():
    global start_time, elapsed_time, ricoh, detections_results
    detections_results = []
    elapsed_time = None
    start_time = time.time()
    if ricoh:
        response_start = ricoh.start_capture()
    else:
        print("Ricoh device not active")
    return render_camera_view()

# Downloads the last recorded file from ricoh camera device
# TODO add to ricoh page and add more options


@ app.route("/download_last/", methods=['POST'])
def download_last():
    global ricoh
    response_start = ricoh.download_last()
    return render_template('index.html')

# Sets the required credentials to access ricoh device API


@ app.route("/post_credentials/", methods=['POST'])
def post_credentials():
    global cameraName, cameraPassword

    cameraName = request.form['cameraName']
    cameraPassword = request.form['cameraPassword']

    return render_settings_view()


# Connects to ricoh device
# hardcoded to SLW camera currently # TODO add params
# Inits ricoh object

@ app.route("/connect_to_ricoh/", methods=['POST'])
def connect_ricoh():
    try:
        global ricoh, ricoh_state

        # Connect to device Wifi AP
        os.system(
            "nmcli d wifi connect {} password {} iface {}"
            .format("THETAYL00160236.OSC", "00160236", "wlp8s0"))

        # Enabling 360 camera
        if not (cameraName and cameraPassword):
            cameraName = 'THETAYL00160236'
            cameraPassword = '00160236'
        ricoh = ricoh_camera(cameraName, cameraPassword)
        print(ricoh.get_device_options())
        # set device in video mode
        ricoh.set_device_videoMode()
        ricoh_state = "Connected"

    # start capture
    except Exception as e:
        print("Error on startup {}".format(e))
    return render_settings_view()


# # Route to obtain frames from depth camera device
@ app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Endpoint to optain detection results...
# Returns list with JSON

# Endpoint which serves the detections data in json format
# Change len(data) == X to increase amount of returned items
# the response contains the latest detection at the first index


@ app.route('/data', methods=["GET", "POST"])
def update_table():
    global detections_results
    data = []

    for detect in reversed(detections_results):
        data.append(detect.toJSON())

        if len(data) == 25:
            break

    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response

# # Returns video stream from depth camera device
# # Runs detection if enabled


def gen():
    global realsense_enabled, camera, enable_detection, detector, detections_results, start_time, current_time, elapsed_time, distance

    if realsense_enabled:
        while realsense_enabled:
            if start_time:
                last_time = current_time
                current_time = time.time()
                elapsed_time = current_time - start_time
            if camera:
                color_image, depth_image, depth_frame, acceleration_x, acceleration_y, acceleration_z, gyroscope_x, gyroscope_y, gyroscope_z = camera.run()
                # Hardcoded distance increase...
                # TODO add real calculation
                distance += 0.001
                ##
                if enable_detection:
                    detection = detector.detect(color_image)
                    color_image, detections = detector.draw_results(
                        detection, color_image, depth_frame, camera.depth_scale, travel_distance=distance, elapsed_time=elapsed_time)

                    # Append the results to the entire list with detection results
                    detections_results.extend(detections)
#                 # encode and return
                ret, jpg = cv2.imencode('.jpg', color_image)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
                # Write frame to disk
                # cv2.imwrite("{}.jpg".format(frame_count), color_image)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True)
