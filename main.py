# main.py

# application related
from flask import Flask, render_template, Response, request, make_response
import requests
from requests.auth import HTTPDigestAuth

from datetime import timedelta, date
import json

# Models
from models.detection import Detection
from models.inspection import InspectionReport

# AI related
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
import sys
#Use cuda flag - default is True; if Opencv is not build with CUDA it would delegate to CPU even if flag is True
use_cuda = True
# Might not need in the end....
# setup illumination on nano
use_gpio = False
if str(platform.platform()).__contains__("Windows"):
    print("On windows, not importing GPIO")
    use_gpio = False
    use_cuda = False
else:
    import RPi.GPIO as GPIO
    use_gpio = True

    # Pin Definitions
    output_pin = 27  # BCM 27, board 13
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
show_ricoh_preview = False
# detector flags
enable_detection = False
detector = None
enabled_detector = ''

# depth camera params
# TODO make the streams selectable from setting
realsense_enabled = False
enable_rgb = True
enable_depth = True
enable_imu = True
# variable to hold travel distance
device_id = None
width = 1280
height = 720
channels = 3
# IMU distance measurement
distance = 0.00

# variable to hold realsense camera obj
camera = None

# List to contain the detections from inspection
detections_results = []
# inspection report
inspection_report = None

# Timer
start_time = None
elapsed_time = None

# Main page
@ app.route('/')
def index():
    global realsense_enabled
    return render_template('index.html')


# Navigate to inspection page
@ app.route('/inspection/')
def render_camera_view():
    ricohInfo = None
    if ricoh:
        ricohInfo = ricoh.ricohState
    return render_template('inspection_screen.html', travel_distance=distance, the_inspection_time=elapsed_time, ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enable_detection, detections=detections_results, report_details=inspection_report, deviceInfo=ricohInfo)

# Navigate to ricoh page
@ app.route('/ricoh/')
def render_ricoh_view(media_files=None):
    global ricoh, ricoh_state, cameraName, cameraPassword

    if ricoh and media_files is None:
        media_files = []
        ricoh_files = ricoh.list_files()
        for mfile in ricoh_files:
            media_files.append(mfile)
        return render_template('ricoh_screen.html', ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, media_files=media_files, deviceInfo=ricoh.ricohState)
    else:
        return render_template('ricoh_screen.html', ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword)


# Navigate to settingds
@ app.route('/settings/')
def render_settings_view():
    return render_template('settings_screen.html', ricoh_status=ricoh_state, cameraName=cameraName, cameraPassword=cameraPassword, illumination_status=illumination, realsense_device_status=realsense_enabled, detector_enabled=enabled_detector)


# Turn illumination on
@ app.route("/illumination_on/", methods=['POST'])
def illumination_on():
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
    global enabled_detector, enable_detection, detector, use_cuda
    if not enable_detection:
        enable_detection = True

    detector = Yolo(confidence_param=0.3, thresh_param=0.5, use_cuda=use_cuda)
    if detector is not None:
        enabled_detector = "Yolo4 tiny detector"
    return render_settings_view()

# Load mask rcnn detector
# TODO add exception handling , returning appropriate response...


@ app.route("/enable_detector_mrcnn/", methods=['POST'])
def enable_detector_mrcnn():
    global enabled_detector, enable_detection, detector, use_cuda

    detector = MRCNN(use_cuda=use_cuda)

    if detector is not None:
        enabled_detector = "Mask RCNN"

    return render_settings_view()

# Disable detector
# TODO add exception handling , returning appropriate response...


@ app.route("/disable_detector/", methods=['POST'])
def disable_detector():
    global enable_detector, enable_detection, detector

    detector = None

    if detector is None:
        print("Detector stopped...")
        enable_detection = False
        enable_detector = ''

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
# Sends the stop capture command
# Requires to have ricoh object set
@ app.route("/stop/", methods=['POST'])
def stop_capture():
    global ricoh, start_time, elapsed_time
    if start_time:
        elapsed_time = time.time() - start_time
    start_time = None
    if ricoh:
        ricoh.stop_capture(withDownload=False)
    else:
        print("Ricoh device not active")

    return render_camera_view()

# Starts capture on ricoh device
# Continuous images/ or video depending on device mode


@ app.route("/start/", methods=['POST'])
def start_capture():
    global start_time, elapsed_time, ricoh, detections_results, distance
    detections_results = []
    distance = 0
    if ricoh:
        ricoh.start_capture()
        elapsed_time = None
        start_time = time.time()
    else:
        print("Ricoh device not active")
    return render_camera_view()

# Downloads the last recorded file from ricoh camera device


@ app.route("/download_last/", methods=['POST'])
def download_last():
    global ricoh
    ricoh.download_last()
    return render_template('index.html')

#  Lists files


@ app.route("/list_files/", methods=['POST', 'GET'])
def list_ricoh_files():
    global ricoh

    files = []
    ricoh_files = ricoh.list_files()
    for mfile in ricoh_files:
        files.append(mfile.toJSON())

    return render_ricoh_view(media_files=files)


# Download file
@ app.route("/download_file/", methods=['POST'])
def download_file():
    global ricoh

    if request.method == 'POST':
        if request.form.get("downloadFileButton"):
            ricoh.download_file(request.form['downloadFileButton'])
            print("Download complete")
    return render_ricoh_view()

# Deletes selected file from table


@ app.route("/delete_file/", methods=['POST'])
def delete_file():
    global ricoh

    if request.method == 'POST':
        if request.form.get("deleteFileButton"):
            ricoh.delete_file([request.form['deleteFileButton']])
            print("Delete complete")
    return render_ricoh_view()

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
# 2nd path is used from Ricoh screen
@ app.route("/connect_to_ricoh/", methods=['POST'])
@ app.route("/connect_to_ricoh_screen/", methods=['POST'])
def connect_ricoh():
    try:
        global ricoh, ricoh_state, cameraName, cameraPassword

        # Connect to device Wifi AP
        # os.system(
        #     "nmcli d wifi connect {} password {} iface {}"
        #     .format("THETAYL00160236.OSC", "00160236", "wlan0"))

        # Enabling 360 camera
        if not (cameraName and cameraPassword):
            # cameraName = 'THETAYL00160236'
            # cameraPassword = '00160236'
            # new cam
            cameraName = 'THETAYL00248307'
            cameraPassword = '00248307'

        ricoh = ricoh_camera(cameraName, cameraPassword)
        print(ricoh.get_device_options())
        # set device in video mode
        ricoh.set_device_videoMode()
        ricoh_state = "Connected"

    # start capture
    except Exception as e:
        print("Error on startup {}".format(e))
    if request.url == 'http://127.0.0.1:5002/connect_to_ricoh/':
        return render_settings_view()
    else:
        return render_ricoh_view()

# Disable ricoh...


@ app.route("/disconnect_ricoh/", methods=['GET', 'POST'])
def disconnect_ricoh():
    global ricoh
    ricoh = None
    return render_ricoh_view()

# Changes camera mode(video/image shooting)


@ app.route("/set_camera_capture_mode/", methods=['GET', 'POST'])
def set_camera_capture_mode():
    global ricoh
    choice = request.form['shootingMode']
    if str(choice).__contains__('video'):
        ricoh.set_device_videoMode()
    else:
        ricoh.set_device_imageMode()
    return render_ricoh_view()

# Sets ricoh device in mode which will set ISO, shutter and aperature with manualy selected values


@ app.route("/set_manual_settings/", methods=['GET', 'POST'])
def set_manual_settings():
    global ricoh
    iso = request.form['ISOsensitivity']
    shutter = request.form['shutterSpeed']
    aperature = request.form['aperature']
    ricoh.set_manual_camera_settings(
        iso, aperature, shutter)
    return render_ricoh_view()


# Sets ricoh device in mode which will set ISO, shutter and aperature automatically
@ app.route("/set_automatic_settings/", methods=['GET', 'POST'])
def set_automatic_settings():
    global ricoh
    ricoh.set_settings_automatically()
    return render_ricoh_view()

# Endpoint which serves the detections data in json format
# Change len(data) == X to increase amount of returned items
# the response contains the latest detection at the first index


@ app.route('/data', methods=["GET", "POST"])
def update_table():
    global detections_results, ricoh
    data = []
    ricoh_data = []
    # get ricoh state
    ricohInfo = None
    if ricoh:
        ricoh.ricohState = ricoh.update_ricoh_state()
        ricohInfo = ricoh.ricohState
        ricoh_data.append(ricohInfo.toJSON())
    # append to data as separate json 'list'
    data.append(ricoh_data)

    detection_data = []
    for detect in reversed(detections_results):
        detection_data.append(detect.toJSON())

        if len(detection_data) == 25:
            break

    data.append(detection_data)

    response = make_response(json.dumps(data))
    response.content_type = 'application/json'
    return response


# # Route to obtain frames from depth camera device
@ app.route('/video_feed')
def video_feed():
    return Response(gen_realsense_feed(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# # Returns video stream from depth camera device
# # Runs detection if enabled


def gen_realsense_feed():
    global realsense_enabled, camera, enable_imu, enable_detection, detector, detections_results, start_time, elapsed_time, distance, norm_avg, norm_avgs, firstAccel
    if realsense_enabled:
        while realsense_enabled:
            if start_time:
                elapsed_time = time.time() - start_time

            if camera:
                color_image, depth_frame, delta_travel_distance, roi_distance = camera.run()
                if enable_imu:
                    distance += delta_travel_distance
                try:
                    if enable_detection:
                        detection = detector.detect(color_image)
                        if detection:
                            color_image, detections = detector.draw_results(
                                detection, color_image, depth_frame, camera.depth_scale, travel_distance=distance, elapsed_time=elapsed_time)
                            # Append the results to the entire list with detection results
                            detections_results.extend(detections)
                except Exception as e:
                    print("exception in detection {}".format(e))
                # Calculate the distance infront of camera
                if depth_frame and camera.depth_scale:
                    # Drawing ROI for obstacle detection
                    try:
                        col_center = (0, 255, 0)
                        height, width, channels = color_image.shape
                        upper_left = ((width // 4) + 200, (height // 4))
                        bottom_right = ((width * 3 // 4) - 200,
                                        (height * 3 // 4) + 100)
                        # draw in the image a BB and Dot at its center, to which distance is measured
                        cv2.rectangle(color_image, upper_left, bottom_right,
                                      col_center, thickness=1)
                        # Find center
                        cx = int(
                            (upper_left[0] + (bottom_right[0] - upper_left[0])*0.5))
                        cy = int(
                            (upper_left[1] + (bottom_right[1] - upper_left[1])*0.5))
                        # add dot at center
                        cv2.circle(color_image, (cx, cy),
                                   radius=3, color=col_center, thickness=3)
                        text = 'Could not compute distance to ROI..'
                        # If there was succesful distance measurement from Realsense, add label with distance
                        if roi_distance:
                            text = 'Distance to ROI  {:.4f}m'.format(
                                roi_distance)
                            if float(roi_distance) <= 0.5:
                                text = 'Distance to ROI  {:.4f}m ! There is something close to camera'.format(
                                    roi_distance)
                        cv2.putText(color_image, text, (upper_left[0], upper_left[1] - 5), cv2.FONT_HERSHEY_SIMPLEX,
                                    0.5, col_center, 2)
                    except Exception as e:
                        # if cant compute distance skip
                        continue
                    # end calculate distance to ROI


#               # encode and return
                ret, jpg = cv2.imencode('.jpg', color_image)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
                # Write frame to disk
                # cv2.imwrite("{}.jpg".format(frame_count), color_image)


@ app.route('/ricoh_feed')
def ricoh_feed():
    return Response(gen_ricoh_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Connects to ricoh and starts preview from camera...
# TODO optimize


def gen_ricoh_feed():
    global ricoh
    url = "".join(("http://192.168.1.1:80/osc/commands/execute"))
    body = json.dumps({"name": "camera.getLivePreview"})
    try:
        response = requests.post(url, data=body, headers={
            'content-type': 'application/json'}, auth=HTTPDigestAuth(ricoh.device_id, ricoh.device_password), stream=True, timeout=5)
        print("Preview posted; checking response")
        if response.status_code == 200:
            bytes = ''
            jpg = ''
            i = 0
            for block in response.iter_content(chunk_size=10000):

                if (bytes == ''):
                    bytes = block
                else:
                    bytes = bytes + block

                # Search the current block of bytes for the jpq start and end
                a = bytes.find(b'\xff\xd8')
                b = bytes.find(b'\xff\xd9')

                # If you have a jpg
                if a != - 1 and b != -1:
                    image = bytes[a:b + 2]
                    bytes = bytes[b + 2:]
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpg\r\n\r\n' + image + b'\r\n\r\n')
        else:
            print("theta response.status_code _preview: {0}".format(
                response.status_code))
            response.close()
    except Exception as err:
        print("theta error _preview: {0}".format(err))


# Can pass desired IP host adress, else uses 127.0.0.1
# Always port 5002
if __name__ == '__main__':
    desired_host = None
    for arg in sys.argv[1:]:
        desired_host = arg

    if not desired_host:
        desired_host = '127.0.0.1'

    app.run(host=desired_host, port=5002, debug=True)
