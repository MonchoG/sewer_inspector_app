import os
import numpy as np
import pyrealsense2 as rs
import time
import cv2
from models.detection import Detection
from detectors.yolo_detector.tracker import EuclideanDistTracker

labelsPath = os.path.join(
    'detectors/mask_rcnn/weights/object_detection_classes_coco.txt')
# derive the paths to the Mask R-CNN weights and model configuration
weightsPath = os.path.join(
    'detectors/mask_rcnn/weights/frozen_inference_graph.pb')
configPath = os.path.join(
    'detectors/mask_rcnn/weights/mask_rcnn_inception_v2_coco_2018_01_28.pbtxt')


class MRCNN:
    def __init__(self, config=configPath,
                 weights=weightsPath,
                 labels=labelsPath,
                 confidence_param=0.5, thresh_param=0.85, use_cuda=False,
                 distance_check=350):
        print("[INFO] loading Mask RCNN from disk...")
        self.net = cv2.dnn.readNetFromTensorflow(
            os.path.join(weights), os.path.join(config))
        if use_cuda:
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        self.LABELS = open(os.path.join(labels)).read().strip().split("\n")
        np.random.seed(42)
        self.COLORS = np.random.randint(
            0, 255, size=(len(self.LABELS), 3), dtype="uint8")
        self.ln = self.net.getLayerNames()
        self.ln = [self.ln[i[0] - 1]
                   for i in self.net.getUnconnectedOutLayers()]
        self.confidence_param = float(confidence_param)
        self.thresh_param = float(thresh_param)
        # Tracker
        self.distance_check = distance_check
        self.tracker = EuclideanDistTracker(self.distance_check)

    def reinit_tracker(self):
        self.tracker = EuclideanDistTracker(self.distance_check)

    def detect(self, input_image):
        blob = cv2.dnn.blobFromImage(input_image, swapRB=True, crop=False)
        self.net.setInput(blob)
        start = time.time()
        (boxes, masks) = self.net.forward(
            ["detection_out_final", "detection_masks"])
        result = (boxes, masks)
        end = time.time()
        # show timing information on Mask RCNN
        print("[INFO] Mask RCNN took {:.6f} seconds".format(end - start))
        return result

    def draw_results_no_depth(self, layerOutputs, input_image):
        return self.draw_results(layerOutputs, input_image)

    def draw_results(self, layerOutputs, input_image, aligned_depth_frame=None, depth_scale=None, travel_distance=None, elapsed_time=None, verbose=None):
        detections = []

        boxes = layerOutputs[0]
        masks = layerOutputs[1]
        confidences = []
        classIDs = []

        tracking_detections = []

        for i in range(0, boxes.shape[2]):
            # extract the class ID of the detection along with the
            # confidence (i.e., probability) associated with the
            # prediction
            classID = int(boxes[0, 0, i, 1])
            confidence = boxes[0, 0, i, 2]

            # filter out weak predictions by ensuring the detected
            # probability is greater than the minimum probability
            if confidence > self.confidence_param:
                # scale the bounding box coordinates back relative to the
                # size of the frame and then compute the width and the
                # height of the bounding box
                (H, W) = input_image.shape[:2]
                box = boxes[0, 0, i, 3:7] * np.array([W, H, W, H])
                (startX, startY, endX, endY) = box.astype("int")
                boxW = endX - startX
                boxH = endY - startY

                # Object tracking
                tracking_detections.append(box.astype("int"))

                # extract the pixel-wise segmentation for the object,
                # resize the mask such that it's the same dimensions of
                # the bounding box, and then finally threshold to create
                # a *binary* mask
                mask = masks[i, classID]
                mask = cv2.resize(mask, (boxW, boxH),
                                  interpolation=cv2.INTER_NEAREST)
                mask = (mask > self.thresh_param)
                # extract the ROI of the image but *only* extracted the
                # masked region of the ROI
                roi = input_image[startY:endY, startX:endX][mask]

                # grab the color used to visualize this particular class,
                # then create a transparent overlay by blending the color
                # with the ROI
                color = self.COLORS[classID]
                blended = ((0.4 * color) + (0.6 * roi)).astype("uint8")

                # store the blended ROI in the original frame
                input_image[startY:endY, startX:endX][mask] = blended

                # draw the bounding box of the instance on the frame
                color = [int(c) for c in color]

                cv2.rectangle(input_image, (startX, startY), (endX, endY),
                              color, 2)
                # Get center and draw dot
                cx = int((startX + endX)/2)
                cy = int((startY + endY)/2)
                cv2.circle(input_image, (cx,  cy), radius=1,
                           color=color, thickness=3)

                distance_mask = None
                distance_center = None

                if aligned_depth_frame and depth_scale:
                    depth = np.asanyarray(aligned_depth_frame.get_data())
                    # Crop depth data using mask of detection:
                    depth = depth[startY:endY, startX:endX][mask].astype(float)

                    # Get data scale from the device and convert to meters
                    depth = depth * depth_scale
                    try:
                        # To compute distance to mask; This computation is more accurate
                        distance_mask, _, _, _ = cv2.mean(depth)
                        # To compute distance from center; This computation is accurate though it distance are not always 100% certain and vary
                        distance_center = aligned_depth_frame.get_distance(
                            int(cx), int(cy))
                    except Exception:
                        print("could not compute distance from mask")

                detect_mod = None
                # draw a bounding box rectangle and label on the image
                if distance_mask or distance_center:
                    text = "{}: {:.4f} : Distance: center{:.4f}m |from mask {:.4f}".format(
                        self.LABELS[classID], confidence, distance_center, distance_mask)
                    detect_mod = Detection(
                        damage_type=self.LABELS[classID], location=travel_distance, distance=distance_center, time_from_start=elapsed_time, bbox=[startX, startY, endX, endY])
                else:
                    # draw the predicted label and associated probability of
                    # the instance segmentation on the frame
                    text = "{}: {:.4f}".format(
                        self.LABELS[classID], confidence)
                    detect_mod = Detection(
                        damage_type=self.LABELS[classID], location=travel_distance, time_from_start=elapsed_time, bbox=[startX, startY, endX, endY])
                cv2.putText(input_image, text, (startX, startY - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                detections.append(detect_mod)
        # Update the tracker
        boxes_ids = self.tracker.update(tracking_detections)
        for box_id in boxes_ids:
            # obtain the tracked objects id and add to image
            x, y, w, h, boxId = box_id
            cv2.putText(input_image, str(boxId), (x, y + 10),
                        cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 0), 2)
            # Iterate over the list with Detection objects and set the IDs
        for i in range(0, len(detections)):
            # If BB points match, assign the ID
            x, y, w, h, boxId = boxes_ids[i]
            detection = detections[i]
            if detection.same_bb([x, y, w, h]):
                detection.set_id(boxId)

        return input_image, detections

    # Calculates the distance to the center of the bounding box
    # Good accuracy in general, not big deviations from ground truth
    def get_distance_center(self, aligned_depth_frame, depth_scale, x, y, w, h, label, verbose=False):
        # center distance measurement
        cx = int((x + (x + w))/2)
        cy = int((y + (y + h))/2)
        try:
            dist = aligned_depth_frame.get_distance(int(cx), int(cy))
            if verbose:
                print("Distance measurement Realsense... Detected {} {} meters away".format(
                    label, dist))
            return dist
        except Exception as e:
            print("Error in distance measurement")
            return None
