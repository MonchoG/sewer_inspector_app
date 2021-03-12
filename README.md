# Sewer inspector application

This project is a python based application which adds functionality that can be used during sewer inspections, by using depth camera device and 360 camera device in order to capture video or image recordings.

The depth, RGB and IMU data from the realsense device can be used to perform obstacle detection and measure distance to detected objects using detph data, run detection algorithms on the RGB output, calculate traveled distance using acceleration data from the IMU stream.

The 360 Ricoh Theta V camera device can be controlled from the application. The application lets the user see device information like battery level and device storage and recording minutes left. The user can also set image or video shooting mode on the camera device, set ISO, shutter speed and aperature settings of the device, download and delete files from device storage. While the 360 camera is not used for recording, live preview can be seen as well.

### Software components

- Flask - lightweight web application python framework.
- OpenCV - Computer vision framework, used for its Deep Learning Neural Network capabilities
- Realsense SDK - SDK that provides the required python modules in order to control and process data from Realsense D435i depth camera device
- Ricoh REST client - a rest client which is used to control and retrieve data from Ricoh Theta V 360 camera device

### Hardware components

- Jetson Nano - embedded computer used to run the software and hardware components
  - USB Wifi adapter is required in order to connect to 360 camera device
  - Ethernet LAN connection is required with shared connection from User PC to Jetson Nano
- Ricoh Theta V 360 camera device
- Realsense D435i camera - connected to USB3.0 port of the Jetson Nano

## Table of contents

- [Sewer inspector application](#sewer-inspector-application)
    - [Software components](#software-components)
    - [Hardware components](#hardware-components)
  - [Table of contents](#table-of-contents)
  - [Setting up project](#setting-up-project)
    - [Testing application](#testing-application)
  - [User manual](#user-manual)
    - [Home screen](#home-screen)
    - [Settings screen](#settings-screen)
    - [Inspection screen](#inspection-screen)
    - [Ricoh screen](#ricoh-screen)
  - [Developer manual](#developer-manual)
    - [Installation procedure](#installation-procedure)
      - [Installing OpenCV](#installing-opencv)
      - [Installing Realsense SDK](#installing-realsense-sdk)
      - [Flask & other python modules](#flask--other-python-modules)
    - [Camera drivers](#camera-drivers)
      - [realsense](#realsense)
      - [ricoh_theta](#ricoh_theta)
    - [Detectors](#detectors)
      - [mask rcnn](#mask-rcnn)
      - [yolo detector](#yolo-detector)
      - [Training](#training)
    - [Models](#models)
    - [Templates](#templates)

## Setting up project

To install and test the project it is required that the required software and modules are installed to the device that will run the application:

- Python
  - Tested on Jetson Nano with Jetpack 4.4.1 and python 3.6.9
  - Tested on Windows with python 3.7.9
- OpenCV - Tested on version 4.4.0. Requires the DNN module in order to perform inferencing using deep learning neural network. There are 2 options here
  - Install opencv contrib module using pip - that way the detector will use CPU processing power
  - Install opencv from source - that way the sdk can be built with CUDA support if the device has CUDA enabled GPU, in order to speed up inferencing time
- Realsense SDK -
  - tested on version 2.40.0 on laptop with Windows 10 and Ubuntu 18.04 
  - tested on version 2.32.1 on Jetson Nano with Jetpack 4.4.1
- Flask - pip installation of Flask module

For detailed installation procedure refer to the Developer manual section

After the required SDKs and Python modules are installed:

- Clone the repository
- Pull files from Git LFS storage - retrieve weights and configuration files for detectors. This procedure requires Git LFS installed on the device. The files can be pulled by executing  ```git lfs pull``` from the command line, while being in the root directory of the repository.

### Testing application

Once everything is installed and available on the host device:

- Connect the host device to the 360 camera access point - the username and password are given at the bottom of the device
- Connect the Realsense camera device to USB3.0 port of the host device
- Start application by typing in root directory of the repository:
 ```python3 main.py 192.168.137.165``` - here the IP address defines where the application can be accessed. If the IP address is ommited the application will be hosted at [127.0.0.1:5002](127.0.0.1:5002)
- Open a browser and navigate to [192.168.137.165:5002](192.168.137.165:5002)

## User manual

The application consists of the following:

### Home screen

Entry point of the application. The user arrives here when he first navigates to the application host link. From here the user can navigate to the other screens.

![image info](./images/Index.JPG)

### Settings screen

From here the user can connect to the 360 camera REST interface

![image info](./images/Settings.JPG)

In order to obtain frames from the devices as well as detections it is required to connect to camera wifi, enable depth device and select and launch a detector. Once everything is enabled the screen looks like this:

![image info](./images/EnabledSettings.JPG)

### Inspection screen

From this screen the user can define and start an inspection and observe live output from Realsense device and detection algorithm if enabled.

- See if connected to ricoh
- Inspection template - enter information about inspection -> submit data to save report to disk
- Inspection preview
  - output from depth camera device
  - computing distance to center of Bounding box to perform obstacle detection
  - detection results(if enabled)
  - Ricoh device info( batery level, capture status, storage, vide minutes, capture mode and file format)
  - Illumination turn on/off (if using GPIO pins for illumination)
  - Time, distance from start ( resets when starting inspection with button)
  - List with detections (if detector enabled) Label, distance from start, timestamp (can add distance to obj)
  - Press stop inspection to stop recording on ricoh and then add detections to report will write the entire list with detection to json file to disk.

![image info](./images/InspectionReport.JPG)

![image info](./images/InspectionDetectionpersonRicoh.JPG)

### Ricoh screen

From this screen the user control the Ricoh camera device. The following functionality is available in this screen:

- Enter camera credentials and connect to device (if no credentials are given connects with default set parameters)
- Start stop recording sequence - by pressing the Start/stop recording buttons the user can start shooting sequence. Depending on the shooting mode its either image sequence or a video.
- Download last file - downloads the last recorded file
- Download/delete from list of files - the user sees lists with files on the device and can download or delete them.
- Live preview - If the device is not used for recording live preview from the device is available
- Perioodically updates the device status information ( batery level, capture status, storage, vide minutes, capture mode and file format)
- Camera settings - set camera shooting settings automatically or manually:
  - Iso, Aperature, shutter speed - 0 will assign automatically, else select from list
  - Capture mode -> image 4k or video 4k

![image info](./images/RicohScreenTop.JPG)

![image info](./images/RicohPreviewandInfo.JPG)

## Developer manual

### Installation procedure

#### Installing OpenCV

The detection functionality of the application is done using Opencv and its Deep learning neural network module. This module can be obtained 2 ways:

- Installation via pip - ```pip install opencv-contrib``` this will install all the required modules to run the detection frameworks but it will be using CPU processing power.

- Build Opencv from source. If built from source, as long as the device has CUDA enabled GPU and CUDA and cuDNN are installed on the system the Opencv can be combiled with GPU support and the DNN module can use the CUDA device for inferencing, which improves detection speeds by a lot.
  
  - On PC - For Ubuntu and Windows installation refer to [Opencv official installation guide](https://docs.opencv.org/master/da/df6/tutorial_py_table_of_contents_setup.html)
  - On Jetson Nano - Download the build script from [here](https://github.com/mdegans/nano_build_opencv)
    - Change version to 4.4.0 or a desired one.
    - Check for the following CMAKE flags in the build script and modify the script accordingly:
      - -D WITH_CUDNN= ON
      - -D OPENCV_DNN_CUDA=ON
      - -D OPENCV_EXTRA_MODULES_PATH=~/opencv_contrib/modules
      - -D PYTHON3_EXECUTABLE= {path_to_python_3_executable} (type ```which python3``` in terminal to find path to python, if not known)

#### Installing Realsense SDK

The realsense SDK is required in order to communicate and operate the Realsense D435i depth camera device with IMU. It is used to perform obstacle detection, measure travelled distance, as well as serving output from the RGB stream in order to be aware of the surroundings of the camera device.

- On Windows 10 and Ubuntu i managed to install the SDK with the required Python modules by following the specified guidelines in the Official [Intel Realsense](https://github.com/IntelRealSense/librealsense) repository.
  
- On Jetson nano:
   To install realsense sdk with python bindings i used [this](https://github.com/JetsonHacksNano/installLibrealsense) script. Open the buildLibrealsense script and change the following in order to install the python bindings and the correct version in order to be able to obtain data from all streams on the D435i camera device:

      - Depending on the Jetson image that is installed on the SD card you might need to update the path to CUDA (For JetPack 4.4.1 i needed to change the CUDA path to version 10.2)
      - Update the Realsense sdk version to 2.32.1 - with this version I was able to run the IMU stream alongside the Depth and RGB streams.
      - Add this CMAKE flag  -D PYTHON3_EXECUTABLE=path/to/python3 (can give =$(which python3) to find path to python, if not known)

#### Flask & other python modules

Flask is a lightweight web application python framework that is used in this project to put a User interface in order to be able to preview the data from the camera devices as well as control them. The project also uses the python requests and json modules in order to communicate with the REST interface of the ricoh camera device.

- The project was tested on python 3.6.9 and 3.7.9
- All other modules required by this project can be installed via pip
- The project was developed and tested on Flask version 1.1.2

### Camera drivers

to run ricoh and RS camera

- realsense - wrapper for rs camera pipeline; threaded; depth, rgb, imu , dinstance calc, travel dist; can run as main for example; parameters expl.

#### realsense

Wrapper class for the Realsense D435i depth camera device. Can start pipeline which provides RGB, depth,infrared, acceleration and/or gyroscope readings.

- init - Initializes Realsense D435i camera device. The camera RGB and Depth stream resolutions are hardcoded, since the acceptable values are from predefined list. Based on the set parameters a profile is created and pipeline is started which provides the data from the device streams that the user requires.
  - if width,height are set the output RGB frame will be resized to those values, else it uses default ones
  - enable_rgb, enable_depth, enable_imu - flags to configure which data streams to enable in the configuration of the device
  - device_id - set this parameter if more than 1 RS device is connected
- stop_pipeline - method to stop the running realsense pipeline
- poll - method to obtain the latest data from the activated streams and update the variables of the realsense object
  - If IMU is enabled it will compute the traveled distance based on the last known acceleration, the current acceleration  and the time between the last and current frames
- calculate_roi_distance - calculates the distance to the center of pre-defined region of interest in the RS camera output frame
- update - retrieves the latest state from the device (imu,rgb and depth streams)
- run_threaded - returns the latest state read by update
- run - reads and returns the latest state of the camera
- shutdown - turns off data streams and powers off Realsense Device
  
#### ricoh_theta

Rest client to consume Ricoh Theta REST API.
  
- initialize - connects to the ricoh device and initializes the device state and options variables
  - device id - name of the ricoh device AP
  - device_password - password to connect to ricoh device AP
- update_ricoh_state - method to update the ricoh device state and options information
- get_request - utility method to perform GET request
  - path - ricoh endpoint to ping with GET request
- post_request - utility method to perform POST request
  - path - ricoh endpoint to ping with POST request
  - body - body with parameters to POST at the Ricoh endpoint specified by path
- get_device_info - aquires basic information of the camera and supported functions.
- get_device_options - returns the following camera options :
  - captureMode
  - videoStitching
  - iso
  - remainingSpace
- set_device_videoMode - sets the device to video mode allowing it to record 4K videos
- set_device_imageMode - sets the device to image mode allowing it to record 4K images
- set_manual_camera_settings - sets the ISO, aperature and shutter speed settings of the camera. If any of the parameters is set it will change that device setting accordingly. If value is 0 it lets device assign automatically.
- set_settings_automatically - lets the device assign settings value automatically
- start/stop capture - starts/stops shooting sequence on the Ricoh device (image sequence of video depending on shooting mode)
- list_files - returns response with the files availablke on the device
- download_last - writes the latest file on the Ricoh device to the host filesystem
- download_files - utility method to download a list of files
- download_file - downloads a single file
- delete_file - deletes the specified file from the device storage.
- pretty_response - utility method to print formatted JSON response

### Detectors

All of the detectors use Opencv DNN and are similar. The difference between the 2 is the framework that is used to read the weights and model from(Darknet and Tensorflow). If depth data and parameters are provided, it is possible compute distance to the detections if enough data is available.

- init method - Loads the configuration, weights and labels of the selected Deep learning neural network. Can set paths to the files manualy by passing as parameters or use the default ones. Can set confidence and threshold parameters. Can set detector to use CUDA backend (if opencv is built with CUDA support, else it will fall back to CPU)
- detect method - accepts input image and infers it using the initialized detector. The method accepts flag verbose which if set to True it will print out the required time to process the input image.
- draw results - needs the return value from the detect method, the input image. Optional parameters are:
  - aligned_depth_frame  and depth scale - if both parameters are set, the method will try to compute the distance to the center of the bounding box of every detection in the image
  - traveled distance - if inspeciton has started and the traveled distance has been measured, this parameter can be given in order to set the distance of the detection from the defined starting position
  - elapsed time - if inspection has started, this parameter can be set in order to include in the detection object, the passed time since the start of the inspection
  - verbose - if set to True it will print information about the detections on the image

#### mask rcnn

- Requires model tensorflow pretrained model and weigts - configuration(.pbtxt), weights(frozen inference graph -  .pb) and labels paths. Can update the default ones in the class file to use without passing those params, or can pass the paths manually. The following detectors can be obtain from Git LFS of the repository:
  - Mask RCNN trained on COCO dataset.
  - TODO add damages weights.

#### yolo detector

- Requires model darkent pretrained model and weights - configuration(.cfg), weights(.weights) and labels paths. Can update the default ones in the class file to use without passing those params, or can pass the paths manually. The following detectors can be obtain from Git LFS of the repository:
  
  - Yolo 3 & 4 trained on COCO dataset
  - Yolo 4 tiny trained on COCO dataset
  - Yolo 3 trained on corrision & infiltration dataset
  - TODO add the new yolo4 weights..

#### Training

- TODO add about Jupyter notebooks training

### Models

- Required model classes for the Flask application
  - detection - model representing single detection during inspection. Contains the label, the location( from starting point), the distance to the object (if can be computed) and the time of the detection since the start
  - inspection - model to collect data regarding the inspected pipeline and store detections data that was captured during the inspection.

### Templates

- The HTML files for the application screens
