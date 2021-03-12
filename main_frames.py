# application related
import platform
import sys
import warnings
import logging

import getopt
from flask import Flask, render_template, Response, request, make_response
import requests
from requests.auth import HTTPDigestAuth
import datetime
from datetime import timedelta, date
import json
# Models
from models.detection import Detection
from models.inspection import InspectionReport
# AI related
import os
from camera_drivers.realsense.RealSense435i import RealSense435i as depth_cam
from camera_drivers.ricoh_theta.thetav import RicohTheta as ricoh_camera
from camera_drivers.ricoh_theta.theta_usb import RicohUsb as ricohUsb

from detectors.yolo_detector.yolo import Yolo
from detectors.mask_rcnn.mrcnn import MRCNN
import cv2
import time

# Use cuda flag - default is True; if Opencv is not build with CUDA it would delegate to CPU even if flag is True
use_cuda = True
# Might not need in the end....
# setup illumination on nano
use_gpio = False
if str(platform.platform()).__contains__("Windows"):
    print("On windows, not enabling CUDA")
    use_cuda = False

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
realsense_enabled = False
enable_rgb = True
enable_depth = True
# Disabled IMU due no need..
enable_imu = False
device_id = None
# Set camera resolution and fps...
width = 1920    
height = 1080
channels = 3
fps = 15
#
write_bag = False
# IMU distance measurement
distance = 0.00
# variable to hold realsense camera obj
camera = None
# Recording to video related
writer = None
write_raw_rgb = False
# video codec..
fourcc = cv2.VideoWriter_fourcc(*'mp4v')            

# List to contain the detections from inspection
detections_results = []
# inspection report
inspection_report = None

# Timer
start_time = None
elapsed_time = None


@ app.route('/')
def index():
    """Calls Flask.render_template to render entry point of application.

    Returns:
        renders index.html
    """
    return render_template('index.html')


@ app.route('/inspection/')
def render_camera_view():
    """Calls Flask.render_template to render inspection page of application. In this screen the user can start inspection as well as observe the output from the Realsense camera device and detection algorithms.

    Returns:
        renders inspection_screen_new.html
    """
    global distance, elapsed_time, realsense_enabled, enable_detection,detections_results,inspection_report
    logging.info("Rendering camera view...")
    try:
        return render_template('inspection_screen_new.html', travel_distance=distance, the_inspection_time=elapsed_time, realsense_device_status=realsense_enabled, detector_enabled=enable_detection, detections=detections_results, report_details=inspection_report)
    except Exception as e:
        logging.error(e)

@ app.route('/ricoh/')
def render_ricoh_view(media_files=None):
    """Calls Flask.render_template to render ricoh device control page of application. This page can be used to communicate and control the 360 camera device.

    Returns:
        renders ricoh_screen.html
    """
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
    """Calls Flask.render_template to render settings page of the application. From the settings screen the user can initilize connection with 360 camera device, start RealSense device and initialize detector.

    Returns:
        renders settings.html
    """
    return render_template('settings_screen.html', realsense_device_status=realsense_enabled, detector_enabled=enabled_detector)


# Turn depth camera on
# TODO add exception handling , returning appropriate response...
@ app.route("/realsense_on/", methods=['POST'])
def start_realsense_camera():
    """Endpoint of the application, which accepts POST request in order to switch the RealSense device on.

    Returns:
        The user will end up in the settings screen by calling the render_settings_view function
    """
    global realsense_enabled, camera
    if not realsense_enabled:
        realsense_enabled = True

    camera = depth_cam(width=width, height=height, channels=channels, fps = fps,
                       enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)
    return render_settings_view()


@ app.route("/realsense_off/", methods=['POST'])
def stop_realsense_camera():
    """Endpoint of the application, which accepts POST request in order to switch the RealSense device OFF.

    Returns:
        The user will end up in the settings screen by calling the render_settings_view function
    """
    global realsense_enabled, camera
    if realsense_enabled:
        realsense_enabled = False
        camera.shutdown()
    else:
        print("Camera is not running...")
    return render_settings_view()


@ app.route("/enable_detector_yolo/", methods=['POST'])
def enable_detector_yolo():
    """Endpoint of the application, accepting POST request in order to load Yolo 4 tiny detector

    TODO add exception handling , returning appropriate response...

    Returns:
        Initializes globaly the selected detector and the user will end up in the settings screen by calling the render_settings_view function
    """
    global enabled_detector, enable_detection, detector, use_cuda
    if not enable_detection:
        enable_detection = True

    thresh = request.form["thresh"]
    confidence = request.form['confidence']
    distance_check = request.form['tracker_dst']

    if thresh == '':
        thresh = float(0.25)

    if confidence == '':
        confidence = float(0.25)

    if distance_check == '':
        distance_check = float(350)

    print('Using thresh and conf {} {}'.format(thresh, confidence))
    detector = Yolo(confidence_param=confidence,
                    thresh_param=thresh, use_cuda=use_cuda, distance_check=distance_check)
    if detector is not None:
        enabled_detector = "Yolo4 tiny detector"
    return render_settings_view()


@ app.route("/enable_detector_yolo_full/", methods=['POST'])
def enable_detector_yolo_full():
    """Endpoint of the application, accepting POST request in order to load Yolo 4 (full model) detector

    TODO add exception handling , returning appropriate response...

    Returns:
        Initializes globaly the selected detector and the user will end up in the settings screen by calling the render_settings_view function
    """
    global enabled_detector, enable_detection, detector, use_cuda
    if not enable_detection:
        enable_detection = True

    thresh = request.form["thresh"]
    confidence = request.form['confidence']
    distance_check = request.form['tracker_dst']

    if thresh == '':
        thresh = float(0.3)

    if confidence == '':
        confidence = float(0.5)

    if distance_check == '':
        distance_check = float(350)

    yolo4_cfg = os.path.join(
        "detectors/yolo_detector/weights/yolo4coco/yolo4.cfg")
    yolo4_weights = os.path.join(
        "detectors/yolo_detector/weights/yolo4coco/yolo4.weights")
    labels = os.path.join(
        "detectors/yolo_detector/weights/yolo-coco/coco.names")

    detector = Yolo(config=yolo4_cfg, weights=yolo4_weights, labels=labels,
                    confidence_param=confidence, thresh_param=thresh, use_cuda=use_cuda, distance_check=distance_check)
    if detector is not None:
        enabled_detector = "Yolo4 detector"
    return render_settings_view()


@ app.route("/enable_detector_mrcnn/", methods=['POST'])
def enable_detector_mrcnn():
    """Endpoint of the application, accepting POST request in order to load Mask RCNN

    TODO add exception handling , returning appropriate response...

    Returns:
        Initializes globaly the selected detector and the user will end up in the settings screen by calling the render_settings_view function.
    """
    global enabled_detector, enable_detection, detector, use_cuda
    if not enable_detection:
            enable_detection = True

    thresh = request.form["thresh"]
    confidence = request.form['confidence']
    distance_check = request.form['tracker_dst']

    if thresh == '':
        thresh = float(0.25)

    if confidence == '':
        confidence = float(0.25)

    if distance_check == '':
        distance_check = float(350)

    detector = MRCNN(confidence_param=confidence, thresh_param=thresh,
                     use_cuda=use_cuda, distance_check=distance_check)

    if detector is not None:
        enabled_detector = "Mask RCNN"

    return render_settings_view()

# Disable detector
# TODO add exception handling , returning appropriate response...


@ app.route("/disable_detector/", methods=['POST'])
def disable_detector():
    """Endpoint of the application, accepting POST request in order to disable detector.

    TODO add exception handling , returning appropriate response...

    Returns:
        Initializes globaly to None and renders settings screen.
    """
    global enable_detector, enable_detection, detector

    detector = None

    if detector is None:
        print("Detector stopped...")
        enable_detection = False
        enable_detector = ''

    return render_settings_view()


@ app.route("/create_report/", methods=['POST'])
def create_report():
    """Method that accepts POST request which will take parameters from the Inspection report form and initializes inspection report object.

    Returns:
        Initializes the inspection report object globaly and renders the inspection screen.
    """
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
    return render_camera_view()


@ app.route("/new_report/", methods=['POST'])
def new_report():
    """Endpoint of the application that can be accesed with POST request. The method will append all detections to the inspection report, write it to json file and then reinitialize the respective inspection report related variables.
    TODO add time to inspection report name ...
    Returns:
        Initializes the inspection report object to None and renders the inspection screen.
    """
    global inspection_report, detections_results, detector

    if detections_results:
        inspection_report.addDetections(detections_results)
    
    inspection_report.write_inspection_file()
    # Clear report variables..
    inspection_report = None
    detections_results = []
    if detector:
        detector.reinit_tracker()
    return render_camera_view()

@ app.route("/stop/", methods=['POST', 'GET'])
def stop_capture():
    """Endpoint of the application which accepts POST request that will stop the ongoing recording on the Ricoh camera device and will release the Realsense frame writer

    Returns:
        Stops the recording sequence on the Ricoh camera device and renders the inspection screen.
    """
    global ricoh, start_time, elapsed_time,write_raw_rgb, writer
    if start_time:
        elapsed_time = time.time() - start_time
    start_time = None
    if ricoh:
        ricoh.stop_capture(withDownload=False)
    else:
        logging.info("Ricoh device not active")

    # if write_raw_rgb and writer:
    #     logging.info("About to release writer")
    #     writer.release()
    #     writer = None
    #     logging.info("writer released...")
    # else:
    #     logging.info("writer not active... Write  raw rgb flag {} | writer == None {}".format(write_raw_rgb, writer == None))
    write_raw_rgb = False
    try:
        # Breaks here randomly......
        return render_camera_view()
        # Breaks above randomly.....
    except Exception as e:
        logging.error(e)

# Starts capture on ricoh device
# Continuous images/ or video depending on device mode


@ app.route("/start/", methods=['POST'])
def start_capture():
    """Endpoint of the application which accepts POST request that will start recording on the Ricoh camera device.

    Returns:
        Starts recording sequence on the Ricoh camera device and renders the inspection screen.
    """
    global start_time, elapsed_time, ricoh, write_raw_rgb, writer, detections_results, distance, inspection_report
    detections_results = []
    distance = 0
    elapsed_time = None
    start_time = time.time()

    if ricoh:
        ricoh.start_capture()
    else:
        logging.info("Ricoh device not active")
    
    write_raw_rgb = True
    # if write_raw_rgb:
    #     # Define codec
    #     video_name = "reports/" + datetime.datetime.now().strftime("%d_%m_%Y %H_%M_%S") + "  " +  inspection_report.city + "_" + inspection_report.street + "_" + inspection_report.pipe_id + "_" + inspection_report.manhole_id +".avi"
    #     if writer:
    #         logging.warning("Writer object is already initialized...")
    #     else:
    #         writer = cv2.VideoWriter(video_name,fourcc, 30.0, (1920,1080))
    #     inspection_report.addVideoFiles([video_name])
    return render_camera_view()


@ app.route("/download_last/", methods=['POST'])
def download_last():
    """Endpoint that accepts POST request which will download the last recorded file from ricoh camera device.
    Returns:
        Downloads the last recorded file from ricoh camera device and renders the 360 camera screen.
    """
    global ricoh
    ricoh.download_last()
    return render_template('index.html')


@ app.route("/list_files/", methods=['POST', 'GET'])
def list_ricoh_files():
    """Endpoint of the application which accepts POST and GET requests, which will list the recordings on the 360 camera device.

    Returns:
        List with the files on the 360 camera device and re-renders the 360 camera screen.
    """
    global ricoh

    files = []
    ricoh_files = ricoh.list_files()
    for mfile in ricoh_files:
        files.append(mfile.toJSON())

    return render_ricoh_view(media_files=files)


# Download file
@ app.route("/download_file/", methods=['POST'])
def download_file():
    """Endpoint of the application which accepts POST request and downloads the select file from the list with files on the 360 camera device.

    Returns:
        Downloads the selected file from the 360 camera device and writes it to disk, then it renders the 360 camera screen.
    """
    global ricoh

    if request.method == 'POST':
        if request.form.get("downloadFileButton"):
            ricoh.download_file(request.form['downloadFileButton'])
            logging.info("Download complete")
    return render_ricoh_view()

# Deletes selected file from table


@ app.route("/delete_file/", methods=['POST'])
def delete_file():
    """Endpoint of the applicaiotn which accepts POST request and deletes the selected file from the list with files on the 360 camera device.

    Returns:
        Renders the 360 camera screen.
    """
    global ricoh

    if request.method == 'POST':
        if request.form.get("deleteFileButton"):
            ricoh.delete_file([request.form['deleteFileButton']])
            logging.info("Delete complete")
    return render_ricoh_view()

# Sets the required credentials to access ricoh device API


@ app.route("/post_credentials/", methods=['POST'])
def post_credentials():
    """Endpoint of the application, which accepts POST request that will take the entered data in the camera name and password fields and initialize the respective variables, in order to be able to connect to ricoh camera device.

    Returns:
        [type]: [description]
    """
    global cameraName, cameraPassword

    cameraName = request.form['cameraName']
    cameraPassword = request.form['cameraPassword']

    return render_settings_view()


@ app.route("/connect_to_ricoh/", methods=['POST'])
@ app.route("/connect_to_ricoh_screen/", methods=['POST'])
def connect_ricoh():
    """Method that initializes ricoh object and connects to the 360 camera device.

    TODO Configure the correct WiFi interface on the jetson nano, in order to connect to camera AP via commandline.
    TODO Remove hardcoded parameters that are used to connect to camera device. ( Currently connects to the lectoraat's Ricoh camera)

    Returns:
        Initializes ricoh object, sets it to video mode and renders the 360 camera screen.
    """
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
        logging.info(ricoh.get_device_options())
        # set device in video mode
        ricoh.set_device_videoMode()
        ricoh_state = "Connected"
    except Exception as e:
        logging.error("Error on startup {}".format(e))
    if request.url == 'http://127.0.0.1:5002/connect_to_ricoh/':
        return render_settings_view()
    else:
        return render_ricoh_view()


@ app.route("/disconnect_ricoh/", methods=['GET', 'POST'])
def disconnect_ricoh():
    """Endpoint of the application that accepts POST and GET requests which will initialize the Ricoh object to None

    Returns:
        Destroys ricoh object and renders 360 camera screen.
    """
    global ricoh
    ricoh = None
    return render_ricoh_view()


@ app.route("/set_camera_capture_mode/", methods=['GET', 'POST'])
def set_camera_capture_mode():
    """Endpoint of the application that accepts POST and GET requests which will change the 360 camera shooting mode (video or image) based on the selection of the user.

    Returns:
    Sets the respective recording mode on the Ricoh 360 camera device and renders the 360 camera screen.
    """
    global ricoh
    choice = request.form['shootingMode']
    if str(choice).__contains__('video'):
        ricoh.set_device_videoMode()
    else:
        ricoh.set_device_imageMode()
    return render_ricoh_view()


@ app.route("/set_manual_settings/", methods=['GET', 'POST'])
def set_manual_settings():
    """Endpoint of the application which accepts POST and GET request. The selected ISO, shutter speed and aperature values will be read from the manual settings form and send request to the 360 camera REST api which will set the respective parameters to the selected values.

    Returns:
        Sets the desired values to the ISO shutter speed and aperature settings of the 360 camera device and rerenders the 360 camera screen.
    """
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
    """Endpoint of the application that accepts POST and GET request, which will let the 360 camera device set the ISO, shutterspeed and aperature settings automatically.

    Returns:
        Sends request to the 360 camera device to set the ISO, shutter speed and aperature settings automatically and rerenders the 360 camera screen.
    """
    global ricoh
    ricoh.set_settings_automatically()
    return render_ricoh_view()

# Endpoint which serves the detections data in json format


@ app.route('/reset_data', methods=["GET", "POST"])
def reset_data():
    """Resets the array that the /data endpoing uses (detection results)

    Returns:
        Empties data arrays and renders the inspection screen
    """
    global detections_results, ricoh, detector
    detections_results = []
    ricoh_data = []
    if detector:
        detector.reinit_tracker()
    return render_camera_view()


@ app.route('/data', methods=["GET", "POST"])
def update_table():
    """Endpoint of the application which accepts POST and GET request, which serves data about the 360 camera device (if connected) and list with detection results.
        Change len(data) == X to increase amount of returned items
        The response contains the latest detection at the first index

    Returns:
        JSON list. The 360 camera device information is at index 0 and list with detection results is placed at index 1.
    """
    global detections_results, ricoh
    data = []
    ricoh_data = []
    # get ricoh state
    ricohInfo = None
    try:
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
    except Exception as e:
        return Response("{'Error with info data stream':'{}'}".format(e), status=440, mimetype='application/json')


# # Route to obtain frames from depth camera device
@ app.route('/video_feed')
def video_feed():
    """Endpoint of the application which returns frames from the Realsense camera device.

    Returns:
        Returns stream with frames from the Realsense camera device.
    """
    try:
        return Response(gen_realsense_feed(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        return Response("{'Error with realsense feed':'{}'}".format(e), status=450, mimetype='application/json')

def gen_realsense_feed():
    """Method that:
     - reads RGB, Depth and IMU streams from the Realsense camera device;
     - updates the traveled distance variable; 
     - performs detection on the RGB stream from the Realsense device if detector is enabled and append the detection to the list with detections
     - Calculates distance to the center of pre-defined ROI in order to perform obstacle detection without the need of detector.
    """
    global realsense_enabled, camera, enable_imu, enable_detection, detector, detections_results, start_time, elapsed_time, distance, ricoh, write_raw_rgb, writer, inspection_reportn
    frame_counter = 0
    try:
        if realsense_enabled:        
            while realsense_enabled:
                if start_time:
                    elapsed_time = time.time() - start_time
                    if ricoh:
                        restart_recording(elapsed_time)

                if camera:
                    try:
                        rgb_frame,color_image, depth_frame, delta_travel_distance, roi_distance = camera.run()
                    except Exception as e:
                        logging.error("Realsense pipeline generated exception {}".format(e))
                    
                    if write_raw_rgb and rgb_frame.any():
                        try:
                            frame_counter +=1
                            image_name = "reports/" + datetime.datetime.now().strftime("%d_%m_%Y %H_%M_%S_%f") + "  " +  inspection_report.city + "_" + inspection_report.street + "_" + inspection_report.pipe_id + "_" + inspection_report.manhole_id +".jpg"
                            cv2.imwrite(image_name,rgb_frame)
                            inspection_report.addImageFiles([image_name])
                        except Exception as e:
                            logging.error('Writer threw exception {}'.format(e))
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
                        logging.error("exception in detection {}".format(e))
                    
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
                    # encode and return
                    ret, jpg = cv2.imencode('.jpg', color_image)
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
    except Exception as e:
        logging.error("Problem in generating feed from Realsense... {}".format(e))


def restart_recording(elapsed_time):
    """Method which will restart the recording sequence on the 360 camera device.
    The recoring sequence will be restarted if:
        * The recording time is close to reaching it maximum limit
        * The device has less than 1GB storage - in this case, the latest recording will be downloaded to disk and will be removed from 360 camera device.
        * If the 360 camera device battery level is below 15% it will stop the recording and download to disk. <- might no be needed
    TODO breaks when trying to stop recording -> download last -> restart recording when storage limit is near limit.
    TODO test extensively.
    Args:
        elapsed_time ([type]): the elapsed time from the start of the recording
    """
    global ricoh
    # Set the restart recording interval in seconds
    recording_checker = 600
    if ricoh:
        if ((elapsed_time % recording_checker) < 1):
            logging.info("Time limit reached, restarting reccording")
            ricoh.stop_capture()
            # time.sleep(3)
            # restart capture
            ricoh.start_capture()
        # Check storage, if less than 1GB download last file, delete and restart capture
        if ricoh.ricohState.storage_left < 1048576000:
            logging.info("Device storage is almost full, downloading last recording...")
            # Download last file to disk and delete to free space
            # !!! Breaks here....
            ricoh.stop_capture(False)
            ricoh.start_capture()
            return
        # If battery level is low save recording & notify user
        # if ricoh.ricohState.battery_level < 0.15:
        #     print("Battery level is low, saving recording...")
        #     ricoh.stop_capture(False)
        #     # ricoh.download_last(False)
        #     # set flag to notify user about batery level
        #     return
    else:
        logging.info("Ricoh not enabled....")


@ app.route('/ricoh_feed')
def ricoh_feed():
    """Endpoint of the application which returns frames from the Ricoh 360 camera device.
    Returns:
        Returns stream with frames from the RRicoh 360 camera device.
    """
    return Response(gen_ricoh_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Connects to ricoh and starts preview from camera...
# TODO optimize

def gen_ricoh_feed():
    """Method that reads frame from livePreview endpoint of Ricoh camera device and streams the frames.
     The resolution of the live preview is limited to 1024x768
    Yields:
        returns the frames from the 360 camera device.
    """
    global ricoh
    url = "".join(("http://192.168.1.1:80/osc/commands/execute"))
    body = json.dumps({"name": "camera.getLivePreview"})
    try:
        response = requests.post(url, data=body, headers={
            'content-type': 'application/json'}, auth=HTTPDigestAuth(ricoh.device_id, ricoh.device_password), stream=True, timeout=5)
        logging.info("Preview posted; checking response")
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
            logging.info("theta response.status_code _preview: {0}".format(
                response.status_code))
            response.close()
    except Exception as err:
        logging.error("theta error _preview: {0}".format(err))


# Can pass desired IP host adress, else uses 127.0.0.1
# Always port 5002
if __name__ == '__main__':
    """Entry point of the application.
       If the main.py script is started from command line, the "desired_host" parameter can be set by giving the desired IP address to host the application.
    """
        # Writting to Log file
    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO, handlers=[
        logging.FileHandler("last_run.log"),
        logging.StreamHandler()
    ])
    
    desired_host = None
    for arg in sys.argv[1:]:
        desired_host = arg

    if not desired_host:
        desired_host = '127.0.0.1'

    try:
        app.run(host=desired_host, port=5002, debug=True, use_reloader=False)
    except Exception as e:
        logging.error("Exception in running app {}".format(e))
