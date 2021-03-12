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
if str(platform.platform()).__contains__("Windows"):
    use_cuda = False

# Application
app = Flask(__name__)

# detector flags
enable_detection = False
detector = None
enabled_detector = ''

# depth camera params
realsense_enabled = False
enable_rgb = True
enable_depth = True
enable_imu = True
device_id = None
width = 1280
height = 720
channels = 3
write_bag = False
# IMU distance measurement
distance = 0.00
# variable to hold realsense camera obj
camera = None

# New ricoh
ricoh_usb = None
write_ricoh = False


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
    global realsense_enabled
    return render_template('index.html')


@ app.route('/inspection/')
def render_camera_view():
    """Calls Flask.render_template to render inspection page of application. In this screen the user can start inspection as well as observe the output from the Realsense camera device and detection algorithms.

    Returns:
        renders inspection_screen.html
    """
    return render_template('inspection_screen_new.html', travel_distance=distance, the_inspection_time=elapsed_time, realsense_device_status=realsense_enabled, detector_enabled=enable_detection, detections=detections_results, report_details=inspection_report)

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
    global realsense_enabled, camera, write_bag

    if not realsense_enabled:
        realsense_enabled = True

    write_bag_path = None
    if write_bag:
        ###
        filename = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        write_bag_path = "realsense_files/" + filename + ".bag"

    camera = depth_cam(width=width, height=height, channels=channels,
                       enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, record_bag=write_bag_path, read_bag=None)

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
    # print(inspection_report.toJSON())
    return render_camera_view()


@ app.route("/new_report/", methods=['POST'])
def new_report():
    """Endpoint of the application that can be accesed with POST request. The method will append all detections to the inspection report, write it to json file and then reinitialize the respective inspection report related variables.
    TODO add time to inspection report name ...
    Returns:
        Initializes the inspection report object to None and renders the inspection screen.
    """
    global inspection_report, detections_results, start_time

    inspection_report.addDetections(detections_results)

    inspection_report.write_inspection_file(date.today().strftime("%d_%m_%Y"))
    # Clear report variables..
    inspection_report = None
    detections_results = []
    detector.reinit_tracker()

    return render_camera_view()


@ app.route('/reset_data', methods=["GET", "POST"])
def reset_data():
    """Resets the array that the /data endpoing uses (detection results)

    Returns:
        Empties data arrays and renders the inspection screen
    """
    global detections_results, detector
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
    global detections_results
    data = []
    ricoh_data = []
    # get ricoh state
    # Smell from WiFi implementation.. cleanup if thats the approach
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
    """Endpoint of the application which returns frames from the Realsense camera device.

    Returns:
        Returns stream with frames from the Realsense camera device.
    """
    return Response(gen_realsense_feed(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


def gen_realsense_feed():
    """Method that:
     - reads RGB, Depth and IMU streams from the Realsense camera device;
     - updates the traveled distance variable;
     - performs detection on the RGB stream from the Realsense device if detector is enabled and append the detection to the list with detections
     - Calculates distance to the center of pre-defined ROI in order to perform obstacle detection without the need of detector.
    """
    global realsense_enabled, camera, enable_imu, enable_detection, detector, detections_results, start_time, elapsed_time, distance
    counter = 0
    if realsense_enabled:
        while realsense_enabled:
            if start_time:
                elapsed_time = time.time() - start_time

            if camera:
                color_image, depth_frame, delta_travel_distance, roi_distance = camera.run()
                # If device connected via USB; write out the frame to disk
                if ricoh_usb and write_ricoh:
                    ricoh_frame = ricoh_usb.get_frame()
                    counter += 1
                    # Writing ricoh frame, whenever realsense frame was read
                    cv2.imwrite(
                        'ricoh_files/ricoh_{}.jpg'.format(counter), ricoh_frame)
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

                # encode and return
                ret, jpg = cv2.imencode('.jpg', color_image)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
                # Write frame to disk
                # cv2.imwrite("{}.jpg".format(frame_count), color_image)


@ app.route('/ricoh_feed')
def ricoh_feed():
    """Endpoint of the application which returns frames from the Ricoh 360 camera device.
    Returns:
        Returns stream with frames from the RRicoh 360 camera device.
    """
    return Response(gen_ricoh_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Reads out frames; To see preview from Ricoh in 4k - visit /ricoh_feed endpoint


def gen_ricoh_feed():
    """Method that reads frame from 360 camera connected via USB
    Yields:
        returns the frames from the 360 camera device.
    """
    # encode and return
    global ricoh_usb, write_ricoh

    counter = 0
    if ricoh_usb:
        while True:
            ricoh_frame = ricoh_usb.get_frame()
            counter += 1
                    # Writing ricoh frame, whenever realsense frame was read
            if write_ricoh:
                cv2.imwrite(
                    'ricoh_files/ricoh_{}.jpg'.format(counter), ricoh_frame)
            ret, jpg = cv2.imencode('.jpg', ricoh_frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')


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
 
    # host addr of app
    desired_host = None

    # Id of usb camera
    ricoh_id = None
    
    # Default writting flags default to False
    write_bag = False
    write_ricoh = False

    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "h", ["host=", "ricoh_id=", "write_bag=", "write_ricoh_frames="])
    except getopt.GetoptError:
        logging.error('invalid arguments')
        sys.exit(2)

    for opt, arg in opts:
        
        if opt == '-h':
            print('python main_new.py --host = host_addr... --ricoh_id= ricoh_device_id... --write_files = write_frames_to_disk...(default is False)')
            sys.exit()
        elif opt in ("--host"):
            desired_host = str(arg)
        elif opt in ("--ricoh_id"):
            ricoh_id = int(arg)
        elif opt in ("--write_bag"):
            ua = str(arg).upper()
            if 'TRUE'.startswith(ua):
                write_bag = True
                logging.warning(
                    "Warning, captured Realsense data will be written to disk in a bag file...")
        elif opt in ("--write_ricoh_frames"):
            ua = str(arg).upper()
            if 'TRUE'.startswith(ua):
                write_ricoh = True
                logging.warning(
                    "Warning, captured 360 frames will be written to disk...")


    # start ricoh cmaera
    if ricoh_id:
        ricoh_usb = ricohUsb(ricoh_id)

        logging.info('Starting usb camera with id {}'.format(ricoh_id))
        # Check if the webcam is opened correctly
        if not ricoh_usb.video.isOpened():
            raise IOError("Cannot open webcam")
    else:
        logging.warning("Warning, script was started without USB camera ID")

    if not desired_host:
        desired_host = '127.0.0.1'
        logging.warning("Warning, starting script with Localhost..")
    logging.info('Starting application at address {}...'.format(desired_host))

    app.run(host=desired_host, port=5002, debug=True)
