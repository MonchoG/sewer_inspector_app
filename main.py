# main.py
import numpy as np
import os

from flask import Flask, render_template, Response
from camera_drivers.realsense.RealSense435i import RealSense435i as depth_cam
from camera_drivers.ricoh_theta.thetav import RicohTheta as ricoh_camera
from detectors.yolo_detector.yolo import Yolo
import cv2
import time

enable_rgb = True
enable_depth = True
enable_imu = False
device_id = None

width = 1280
height = 720
channels = 3





app = Flask(__name__)


enable_detection = False
detector = None

realsense_enabled = False
camera = None

ricoh = None

@app.route('/')
def index():
    global realsense_enabled
    return render_template('index.html', realsense_device_status=realsense_enabled)

@app.route("/realsense_on/", methods=['POST'])
def start_realsense_camera():
    global realsense_enabled, camera
    print(realsense_enabled)
    if not realsense_enabled :
        realsense_enabled = True
    
    camera = depth_cam(width=width, height=height, channels=channels,
                    enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)
    return index()

@app.route("/realsense_off/", methods=['POST'])
def stop_realsense_camera():
    global realsense_enabled, camera
    if realsense_enabled :
        realsense_enabled = False
        camera.shutdown()  
    else:
        print("Camera is not running...")
    return index()


@app.route("/enable_detector/", methods=['POST'])
def enable_detector():
    global enable_detection, detector
    if not enable_detection :
        enable_detection = True
    
    detector = Yolo(confidence_param=0.3, thresh_param=0.5)
    return index()

@app.route("/disable_detector/", methods=['POST'])
def disable_detector():
    global enable_detection, camera
    if enable_detection :
        enable_detection = False
        detector = None
    print("Detector stopped...")
    return index()



@app.route("/stop/", methods=['POST'])
def stop_capture():
    global ricoh
    os.system(
        "nmcli d wifi connect {} password {} iface {}"
        .format("THETAYL00160236.OSC", "00160236", "wlp8s0"))
    response_stop = ricoh.stop_capture(False)
    return render_template('index.html')


@app.route("/start/", methods=['POST'])
def start_capture():
    response_start = ricoh.start_capture()
    return render_template('index.html')


@app.route("/download_last/", methods=['POST'])
def download_last():
    response_start = ricoh.download_last()
    return render_template('index.html')

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



def gen():
    global realsense_enabled, camera, enable_detection, detector
    if realsense_enabled:
        while realsense_enabled:
            if camera:
                color_image, depth_image, depth_frame, acceleration_x, acceleration_y, acceleration_z, gyroscope_x, gyroscope_y, gyroscope_z = camera.run()
                
                if enable_detection:
                    detection = detector.detect(color_image)
                    color_image = detector.draw_results(
                        detection, color_image, depth_frame, camera.depth_scale)

                # encode and return
                ret, jpg = cv2.imencode('.jpg', color_image)
                yield (b'--frame\r\n'
                    b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
                #cv2.imwrite("{}.jpg".format(frame_count), color_image)


@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=True)
