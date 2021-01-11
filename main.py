# main.py
import numpy as np
import os

from flask import Flask, render_template, Response, request
from camera_drivers.realsense.RealSense435i import RealSense435i as depth_cam
from camera_drivers.ricoh_theta.thetav import RicohTheta as ricoh_camera
from detectors.yolo_detector.yolo import Yolo
from detectors.mask_rcnn.mrcnn import MRCNN
import cv2
import time

from camera import VideoCamera

# Uncomment on nano to import GPIO modules
#import RPi.GPIO as GPIO

# Pin Definitions
output_pin = 23  # BCM pin 23, BOARD pin 16
output_pin2 = 27  # BCM 27, board 13
output_pin3 = 18  # BCN 18, board 12
# Uncomment on nano to init gpio pins...
# GPIO.setmode(GPIO.BCM)  # BCM pin-numbering scheme from Raspberry Pi
# # set pin as an output pin with optional initial state of LOW
# GPIO.setup(output_pin, GPIO.OUT, initial=GPIO.LOW)
# GPIO.setup(output_pin2, GPIO.OUT, initial=GPIO.LOW)
# GPIO.setup(output_pin3, GPIO.OUT, initial=GPIO.LOW)
# curr_value = GPIO.LOW
# Ilumination
illumination_on = False

illumination = "OFF"

# depth camera params
enable_rgb = True
enable_depth = True
enable_imu = False
device_id = None

width = 1280
height = 720
channels = 3


# Application
app = Flask(__name__)


# Ricoh credentials
cameraName = None
cameraPassword = None


enable_detection = "OFF"
detector = None

realsense_enabled = False
camera = None

ricoh = None


@app.route('/')
def index():
    global realsense_enabled
    return render_template('index.html', cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection)


# Turn illumination on
# TODO cleanup
@app.route("/illumination_on/", methods=['POST'])
def illumination_on():
    # uncomment on nano
    # global output_pin , curr_value
    # curr_value = GPIO.HIGH
    # GPIO.output(output_pin, curr_value)
    global illumination

    illumination = "ON"
    return index()


# Turn illumination off
# TODO cleanup
@app.route("/illumination_off/", methods=['POST'])
def illumination_off():
    # uncomment on nano
    # global output_pin , curr_value
    # curr_value = GPIO.LOW
    # GPIO.output(output_pin, curr_value)
    global illumination
    illumination = "OFF"
    return index()


# Turn depth cam on
@app.route("/realsense_on/", methods=['POST'])
def start_realsense_camera():
    global realsense_enabled, camera
    print(realsense_enabled)
    if not realsense_enabled:
        realsense_enabled = True

    camera = depth_cam(width=width, height=height, channels=channels,
                       enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)
    return index()

# Turn depth cam off


@app.route("/realsense_off/", methods=['POST'])
def stop_realsense_camera():
    global realsense_enabled, camera
    if realsense_enabled:
        realsense_enabled = False
        camera.shutdown()
    else:
        print("Camera is not running...")
    return index()

# Load yolo detector


@app.route("/enable_detector_yolo/", methods=['POST'])
def enable_detector_yolo():
    global enable_detection, detector
    if not enable_detection:
        enable_detection = True

    detector = Yolo(confidence_param=0.3, thresh_param=0.5)
    if detector is not None:
        enable_detection = "Yolo detector"
    return index()


@app.route("/enable_detector_mrcnn/", methods=['POST'])
def enable_detector_mrcnn():
    global enable_detection, detector

    detector = MRCNN(use_cuda=True)

    if detector is not None:
        enable_detection = "Mask RCNN"

    return index()

# Disable detector


@app.route("/disable_detector/", methods=['POST'])
def disable_detector():
    global enable_detection

    detector = None

    if detector is None:
        print("Detector stopped...")
        enable_detection = "OFF"

    return index()


# Stop theta video capture
# Connects to device wifi # TODO check how this works...
# Sends the stop capture command
# Requires to have ricoh object set
@app.route("/stop/", methods=['POST'])
def stop_capture():
    global ricoh
    os.system(
        "nmcli d wifi connect {} password {} iface {}"
        .format("THETAYL00160236.OSC", "00160236", "wlp8s0"))
    response_stop = ricoh.stop_capture(False)
    return render_template('index.html')

# Starts capture on ricoh device
# Continuous images/ or video depending on device mode


@app.route("/start/", methods=['POST'])
def start_capture():
    response_start = ricoh.start_capture()
    return render_template('index.html')

# Downloads the last recorded file from ricoh camera device


@app.route("/download_last/", methods=['POST'])
def download_last():
    response_start = ricoh.download_last()
    return render_template('index.html')


@app.route("/post_credentials/", methods=['POST'])
def post_credentials():
    global cameraName, cameraPassword

    cameraName = request.form['cameraName']
    cameraPassword = request.form['cameraPassword']

    return index()

# Connects to ricoh device
# hardcoded to SLW camera currently # TODO add params
# Inits ricoh object


@app.route("/connect_to_ricoh/", methods=['POST'])
def connect_ricoh():
    try:
        global ricoh

        # Connect to device Wifi AP
        os.system(
            "nmcli d wifi connect {} password {} iface {}"
            .format("THETAYL00160236.OSC", "00160236", "wlp8s0"))

        # Enabling 360 camera
        slw_cam = 'THETAYL00160236'
        slw_cam_pass = '00160236'
        ricoh = ricoh_camera(slw_cam, slw_cam_pass)
        print(ricoh.get_device_options())
        # set device in video mode
        ricoh.set_device_videoMode()
    # start capture
    except Exception as e:
        print("Error on startup {}".format(e))
    return render_template('index.html')


# # Path to obtain frames from depth camera device
# @app.route('/video_feed')
# def video_feed():
#     return Response(gen(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')


# # Returns video stream from depth camera device
# # Runs detection if enabled
# def gen():
#     global realsense_enabled, camera, enable_detection, detector
#     if realsense_enabled:
#         while realsense_enabled:
#             if camera:
#                 color_image, depth_image, depth_frame, acceleration_x, acceleration_y, acceleration_z, gyroscope_x, gyroscope_y, gyroscope_z = camera.run()

#                 if enable_detection:
#                     detection = detector.detect(color_image)
#                     color_image = detector.draw_results(
#                         detection, color_image, depth_frame, camera.depth_scale)

#                 # encode and return
#                 ret, jpg = cv2.imencode('.jpg', color_image)
#                 yield (b'--frame\r\n'
#                        b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
#                 #cv2.imwrite("{}.jpg".format(frame_count), color_image)


def gen(camera):
    while True:
        frame = camera.get_frame()
        detection = detector.detect(frame)
        color_image = detector.draw_results_no_depth(detection, frame)
        ret, jpeg = cv2.imencode('.JPEG', color_image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
