# from mrcnn import MRCNN
import cv2
import numpy as np
from detectors.yolo_detector.yolo import Yolo

# from damage_detection.mask_rcnn.mrcnn import MRCNN
import sys
import os
#mask_rnn = MRCNN()
yolo4_tiny_cfg_sewer = os.path.join(
    "detectors/yolo_detector/weights/yolo4tiny_sewer/custom-yolov4-tiny-detector_5.cfg")
yolo4_tiny_weights_sewer = os.path.join(
    "detectors/yolo_detector/weights/yolo4tiny_sewer/custom-yolov4-tiny-detector_5_best.weights")
yolo4_tiny_labels_sewer = os.path.join(
    "detectors/yolo_detector/weights/yolo4tiny_sewer/obj.names")

yolo_detector = Yolo(config=yolo4_tiny_cfg_sewer,
                     weights=yolo4_tiny_weights_sewer,
                     labels=yolo4_tiny_labels_sewer)

# Create a VideoCapture object and read from input file
# If the input is the camera, pass 0 instead of the video file name
cap = cv2.VideoCapture('500.mpg')
frame_width = int(cap.get(3))
frame_height = int(cap.get(4))

out = cv2.VideoWriter('500_det5_dmg_yolo4tiny.avi', cv2.VideoWriter_fourcc(
    'M', 'J', 'P', 'G'), 29, (frame_width, frame_height))


# Check if camera opened successfully
if (cap.isOpened() == False):
    print("Error opening video stream or file")

# Read until video is completed
while(cap.isOpened()):
    # Capture frame-by-frame
    ret, frame = cap.read()
    if ret == True:

        # Display the resulting frame
        detection = yolo_detector.detect(frame)
        color_image, detections = yolo_detector.draw_results_no_depth(
                                detection, frame)
        draw,detections = yolo_detector.draw_results(detection, color_image, 0, 1)
        out.write(draw)

        cv2.imshow("drawn", draw)
        if cv2.waitKey(1) == 27:
            print("Breaking by key")
            cv2.destroyAllWindows()
            break

        # Press Q on keyboard to  exit
        # if cv2.waitKey(25) & 0xFF == ord('q'):
        #

    # Break the loop
    else:
        break

# When everything done, release the video capture object
cap.release()
out.release()

# Closes all the frames
cv2.destroyAllWindows()
