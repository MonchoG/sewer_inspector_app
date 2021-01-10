# main.py
import numpy as np

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

camera = depth_cam(width=width, height=height, channels=channels,
                       enable_rgb=enable_rgb, enable_depth=enable_depth, enable_imu=enable_imu, device_id=device_id)

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route("/stop/", methods=['POST'])
def stop_capture():
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



def gen(yolo, ricoh):
    
    while True:
        color_image, depth_image, depth_frame, acceleration_x, acceleration_y, acceleration_z, gyroscope_x, gyroscope_y, gyroscope_z = camera.run()
        detection = yolo.detect(color_image)

        color_image = yolo.draw_results(
            detection, color_image, depth_frame, camera.depth_scale)

        # encode and return
        ret, jpg = cv2.imencode('.jpg', color_image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpg\r\n\r\n' + jpg.tobytes() + b'\r\n\r\n')
        #cv2.imwrite("{}.jpg".format(frame_count), color_image)


@app.route('/video_feed')
def video_feed():
    return Response(gen(yolo, ricoh),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':

    # Enabling depth cam
    try:

        yolo = Yolo(confidence_param=0.3, thresh_param=0.5)

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
    app.run(host='127.0.0.1', debug=True)
