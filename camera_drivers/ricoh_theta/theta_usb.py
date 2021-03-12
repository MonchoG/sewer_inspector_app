import cv2

class RicohUsb(object):
    def __init__(self, device_id):
        # Using OpenCV to capture from device 0. If you have trouble capturing
        # from a webcam, comment the line below out and use a video file
        # instead.
        self.video = cv2.VideoCapture(device_id)
        self.video.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        self.video.set(cv2.CAP_PROP_FRAME_HEIGHT, 1920)
        # If you decide to use video.mp4, you must have this file in the folder
        # as the main.py.
        # self.video = cv2.VideoCapture('video.mp4')
    
    def __del__(self):
        self.video.release()
    
    def get_frame(self):
        success, image = self.video.read()
        # We are using Motion JPEG, but OpenCV defaults to capture raw images,
        # so we must encode it into JPEG in order to correctly display the
        # video stream.
        # return jpeg.tobytes()
        return image
    
# cam = RicohUsb(1)

# # Check if the webcam is opened correctly
# if not cam.video.isOpened():
#     raise IOError("Cannot open webcam")

# fourcc = cv2.VideoWriter_fourcc(*'XVID')
# out = cv2.VideoWriter('output.mp4',fourcc, 20.0, (3840,1920))

# while True:
#     frame = cam.get_frame()
#     cv2.imshow('Input', frame)
#     #out.write(frame)


#     c = cv2.waitKey(1)
#     if c == 27:
#         break
    
# cam.video.release()
# out.release()
# cv2.destroyAllWindows()