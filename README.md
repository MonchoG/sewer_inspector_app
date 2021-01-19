# sewer_inspector_app
This project is a python based application which adds functionality that can be used during sewer inspections in order to automate the inspection and detection of damages.

To test perform the steps in the Setup section and then start the file main.py. The script can be started with parameter for desired IP at which the application will be accessible (for example python3 main.py 192.168.137.165 - in this case the application will be accesible at 192.168.137.165:5002).

The project consists of the following :
## Software components
- Flask - lightweight web application python framework
- OpenCV - Computer vision framework, used for its Deep Learning Neural Network capabilities
- Realsense SDK - SDK that provides the required python modules in order to control and process data from Realsense D435i depth camera device
- Ricoh REST client - a rest client which is used to control and retrieve data from Ricoh Theta V 360 camera device
## Hardware components
- Jetson Nano - embedded computer used to run the software and hardware components
- Ricoh Theta V 360 camera device
- Realsense D435i camera
  
# Setup
- The project was tested on python 3.6.9 and 3.7.9
- The project was tested with version for OpenCV is 4.4.0 built from source (not mandatory to build from source). In general any version of OpenCV which has the required DNN module should work - this means that the contrib version of opencv is required
- The project was tested with version of Realsense SDK is 2.40.0 on Windows
- The project was developed and tested on Flask version 1.1.2

1. Clone the repository
2. Install required modules
   1. OpenCV - it is required to build from source, if you want to use the DNN module of the framework with GPU processing power, otherwise it will run on CPU which is a lot slower.
      1. For quick install via Pip - pip3 install opencv-contrib-python
      2. The second option is to build from source - 
         1. For PC refer to Opencv documentation - [link](https://docs.opencv.org/master/d7/d9f/tutorial_linux_install.html)
         2. For jetson nano I used script - [link](https://github.com/mdegans/nano_build_opencv)
            - Check if Opencv version satisfies - I updated to 4.4.0
            - Add this CMAKE flag  -D PYTHON3_EXECUTABLE=path/to/python3 (can give =$(which python3) to find path to python, if not known)
            - Add this CMAKE flag -D WITH_OPENCV_DNN_CUDA=ON
            - Add this CMAKE flag -D OPENCV_DNN_CUDA=ON
   2. Realsense SDK with Python bindings
      1. On windows:
      2. On Jetson nano:
         1. To install realsense sdk with python bindings i used [this](https://github.com/JetsonHacksNano/installLibrealsense) script
            - Depending on the Jetson image that is installed on the SD card you migth need to update the path to CUDA (For JetPack 4.4 i needed to change to CUDA version 10.2)
            - Open the buildLibrealsense script and change:
              - path to cuda - for jetson updating the path to the correct version is enough
              - Add this CMAKE flag  -D PYTHON3_EXECUTABLE=path/to/python3 (can give =$(which python3) to find path to python, if not known)
    3. The rest of the required modules can be installed via pip, if they are not already available within your python environment. 


# Contents
## Camera drivers
### realsense
Wrapper class for the Realsense D435i depth camera device. Can start pipeline which provides RGB, depth,infrared, acceleration and/or gyroscope readings. (On linux IMU requires extra packages with instalation of SDK check Realsense building from sources..)
### ricoh_theta
Client to communicate with Ricoh Theta V REST api. Can control the camera settings, start/stop recording, transfer images and videos. Uses python requests module.
## Detectors
All of the detectors use Opencv DNN and are similar. The difference between the 2 is the framework that is used to read the weights and model from(Darknet and Tensorflow). If depth data and parameters are provided, it is possible compute distance to the detections if enough data is available
### mask rcnn
- Requires model tensorflow pretrained model and weigts - configuration(.pbtxt), weights(frozen inference graph -  .pb) and labels paths. Can update the default ones in the class file to use without passing those params, or can pass the paths manually
  - Pretrained model on COCO can be found at : 
### yolo detector
- Requires model darkent pretrained model and weights - configuration(.cfg), weights(.weights) and labels paths. Can update the default ones in the class file to use without passing those params, or can pass the paths manually
  - Pretrained model on COCO can be found at : 
## Models
- Required model classes for the Flask application
## Templates
- The HTML files for the application
