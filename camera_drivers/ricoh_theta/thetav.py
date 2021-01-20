import requests
import json
from requests.auth import HTTPDigestAuth
import time
# This is required if executing main


if __name__ == "__main__":
    from ricoh_models.ricoh_media_file import MediaFile
    from ricoh_models.ricoh_device_state import RicohState
else:
    from camera_drivers.ricoh_theta.ricoh_models.ricoh_media_file import MediaFile
    from camera_drivers.ricoh_theta.ricoh_models.ricoh_device_state import RicohState


# Client wrapper to access ricoh theta V through WiFi api and control device

execute_command = '/osc/commands/execute'


class RicohTheta:
    def __init__(self, device_id, device_password):
        self.base_url = 'http://192.168.1.1'
        self.device_id = device_id
        self.device_password = device_password
        self.captureStatus = 'idle'  # default
        device_state = self.get_device_state()
        device_option = self.get_device_options()

        # Grab shooting status ## shooting | idle means no recording
        self.captureStatus = device_state["state"]["_captureStatus"]

        # set device storage prop for easy access
        self.storage_uri = device_state["state"]["storageUri"]

        battery_level = device_state["state"]["batteryLevel"]
        storage_left = device_option["results"]["options"]["remainingSpace"]
        capture_mode = device_option["results"]["options"]["captureMode"]
        file_format = device_option["results"]["options"]["fileFormat"]
        remaining_video_seconds = device_option["results"]["options"]["remainingVideoSeconds"]
        # set device state
        self.ricohState = RicohState(
            battery_level, self.captureStatus, storage_left, capture_mode, file_format, remaining_video_seconds)
        # last recorded vid
        self.last_video = None

        # Flag
        self.last_command_id = None

    def update_ricoh_state(self):
        device_state = self.get_device_state()
        device_option = self.get_device_options()
        # set device storage prop for easy access
        self.storage_uri = device_state["state"]["storageUri"]

        captureState = device_state["state"]["_captureStatus"]
        battery_level = device_state["state"]["batteryLevel"]
        storage_left = device_option["results"]["options"]["remainingSpace"]
        capture_mode = device_option["results"]["options"]["captureMode"]
        file_format = device_option["results"]["options"]["fileFormat"]
        remaining_video_seconds = device_option["results"]["options"]["remainingVideoSeconds"]

        # set device state
        self.ricohState = self.ricohState.update_state(
            battery_level, captureState, storage_left, capture_mode, file_format, remaining_video_seconds)
        return self.ricohState

    # Base url is the ip 'http://192.168.1.1'
    # path should be /path/method for ex '/osc/info'

    def get_request(self, path):
        return requests.get(self.base_url + path)

    # Base url is the ip 'http://192.168.1.1'
    # path should be /path/method for ex '/osc/info'
    # body is specific to the endpoint JSON dict with parameters
    def post_request(self, path, body=None):
        post = requests.post(self.base_url + path, data=body,  headers={
            'content-type': 'application/json'}, auth=HTTPDigestAuth(self.device_id, self.device_password), timeout=5)
        return post

    # Calls the "osc/info" endpoint of ricoh Api using GET
    # Acquires basic information of the camera and supported functions.
    def get_device_info(self):
        request = self.get_request("/osc/info")
        return request.json()

    # Calls the "/osc/commands/execute" endpoint of ricoh Api using post
    # Returns the following camera options : captureMode,videoStitching,iso,remainingSpace
    def get_device_options(self):
        body = json.dumps({"name": "camera.getOptions",	"parameters":
                           {"optionNames": [
                               "captureMode",
                               "_imageStitching",
                               "videoStitching",
                               "fileFormat",
                               "fileFormatSupport",
                               "previewFormat",
                               "iso",
                               "remainingSpace",
                               "remainingVideoSeconds"]
                            }})
        request = self.post_request("/osc/commands/execute", body)
        return request.json()

    # Calls the "/osc/commands/execute" endpoint of ricoh Api using post
    # Sets the device to video mode, the parameters can be modified according to the API and need
    # Sets to 4k Mp4
    def set_device_videoMode(self):
        body = json.dumps({"name": "camera.setOptions",	"parameters": {	"options": {
            "captureMode": "video",	"sleepDelay": 1200, "offDelay": 600, "videoStitching": "ondevice",
            # "fileFormat": {"type": "mp4", "width": 3840, "height": 1920,  "_codec": "H.264/MPEG-4 AVC"},
            "_microphoneChannel": "1ch", "_gain": "mute",	"_shutterVolume": 100,
            "previewFormat": {"width": 3840, "height": 1920, "framerate": 30}}}})
        request = self.post_request("/osc/commands/execute", body)
        return request.json()

    # Calls the "/osc/commands/execute" endpoint of ricoh Api using post
    # Sets the device to video mode, the parameters can be modified according to the API and need
    def set_device_imageMode(self):
        body = json.dumps({"name": "camera.setOptions",
                           "parameters": {
                               "options": {
                                   "captureMode": "image",	"sleepDelay": 1200, "offDelay": 600, "_imageStitching": "dynamicAuto",
                                   # "fileFormat": {"type": "jpeg", "width": 5376, "height": 2688},
                                   "_microphoneChannel": "1ch", "_gain": "mute",	"_shutterVolume": 100,
                                   "previewFormat": {"width": 3840, "height": 1920, "framerate": 30}}}})
        request = self.post_request("/osc/commands/execute", body)
        return request.json()

    # Calls the "/osc/commands/execute" endpoint of ricoh Api using post
    # Sets the device to video mode, the parameters can be modified according to the API and need
    def set_manual_camera_settings(self, iso=None, aperature=None, shutterSpeed=None):
        if not iso:
            iso = 0
        if not aperature:
            aperature = 0
        if not shutterSpeed:
            shutterSpeed = 0

        body = json.dumps({"name": "camera.setOptions",
                           "parameters": {
                               "options": {
                                   "exposureProgram": 1,
                                   "iso": int(iso),
                                   "aperature": float(aperature),
                                   "shutterSpeed":float(shutterSpeed)}}})
        request = self.post_request("/osc/commands/execute", body)
        return request.json()
     # Calls the "/osc/commands/execute" endpoint of ricoh Api using post
    # Sets the device to video mode, the parameters can be modified according to the API and need

    def set_settings_automatically(self):
        body = json.dumps({"name": "camera.setOptions",
                           "parameters": {
                               "options": {
                                   "exposureProgram": 2}}})
        request = self.post_request("/osc/commands/execute", body)
        return request.json()
    # Calls the "osc/state" endpoint of ricoh Api using POST
    # Acquires the camera states. Use CheckForUpdates to check whether the state object has changed its contents.
    #  Returns json object containing
    # { fingerprint : String, Takes a unique valueper current state ID.
    #  state : object, Camera state (refer to Api docs for all props of this object)}
    # For ex. device storage and battery level can be extracted from this response.

    def get_device_state(self):
        request = self.post_request("/osc/state")
        json = request.json()

        self.captureStatus = json["state"]["_captureStatus"]
        return json

    # Starts continuous shooting.
    # The shooting method changes according to the shooting mode (captureMode) and _mode settings.
    def start_capture(self):
        body = json.dumps({"name": "camera.startCapture"})
        #
        self.last_command_id = "camera.startCapture"
        #
        request = self.post_request("/osc/commands/execute", body)
        print(request.json())
        self.update_ricoh_state()
        return request.json()

    # Stops continuous shooting.
    # The output “results” is none when the shooting method is the interval shooting with limited number, the composite shooting, multi bracket shooting or time shift shooting.
    # In case of the video shooting or the limitless interval shooting, it is as below.
    # set withDownload to True if want to save the videos immediatly after posting the request
    # returns the response from the stopCapture command.
    def stop_capture(self, withDownload=False):
        body = json.dumps({"name": "camera.stopCapture"})
        #
        self.last_command_id = "camera.stopCapture"
        #
        request = self.post_request("/osc/commands/execute", body)
        json_response = request.json()
        self.last_video = json_response["results"]["fileUrls"]
        if withDownload:
            self.download_files(json_response["results"]["fileUrls"])

        self.update_ricoh_state()

        return json_response

    # List files
    def list_files(self):
        request = requests.post(self.base_url + execute_command, json={'name': 'camera.listFiles',
                                                                               'parameters':
                                                                               {"fileType": "all",
                                                                                "entryCount": 10}})
        result = request.json()
        media_files = []
        if result['state'] == 'done':
            for media_file in result['results']['entries']:
                medFile = MediaFile()
                medFile = medFile.parse_media_file_response(media_file)
                media_files.append(medFile)
        return media_files

    def download_last(self):
        self.download_files(self.last_video)

    # Downloads the files from the links specified in files
    # files is list with download urls from Ricoh Storage

    def download_files(self, files):
        file_count = 0
        for a_file in files:
            response = requests.get(a_file.fileUrl, stream=True)
            # reponse returns file path link, the name of the file starts from char 67
            file_name = a_file[67:]
            with open(file_name, 'wb') as f:
                # write the contents of the response (r.content)
                # to a new file in binary mode.
                f.write(response.content)
            file_count += 1
        print("[INFO] All files downloaded...")

    # Download single file
    def download_file(self, file):
        if isinstance(file, str):
            # if file is string ( file link, parse the link to get file name and extension)
            file_name = file[(file.rfind('/')+1):]
            response = requests.get(file, stream=True)
        else:
            # else file is object of type mediaFile
            file_name = file.name
            response = requests.get(file.fileUrl, stream=True)

        # reponse returns file path link, the name of the file starts from char 67
        with open(file_name, 'wb') as f:
            # write the contents of the response (r.content)
            # to a new file in binary mode.
            f.write(response.content)
        print("[INFO] Downloading file {}complete...".format(file_name))

    def delete_file(self, files):
        request = requests.post(self.base_url + execute_command, json={'name': 'camera.delete',
                                                                               'parameters':
                                                                               {"fileUrls": files}})
        if request.status_code == 200:
            return True
        else:
            return False

# Utils


def pretty_response(response):
    return json.dumps(response, indent=2, sort_keys=True)
###


if __name__ == "__main__":

    new_cam = 'THETAYL00248307'
    new_cam_pass = '00248307'
    slw_cam = 'THETAYL00160236'
    slw_cam_pass = '00160236'

    ricoh = RicohTheta(new_cam, new_cam_pass)
    # print(ricoh.ricohState.capture_mode)
    # ricoh.set_device_imageMode()
    # ricoh.update_ricoh_state()
    # print(ricoh.ricohState.capture_mode)

    print(ricoh.get_device_state())

    ricoh.start_capture()
    print(ricoh.get_device_state())
    time.sleep(1)
    print(ricoh.get_device_state())
    time.sleep(3)
    ricoh.stop_capture()
    print(ricoh.get_device_state())

    # ricoh_options = ricoh.get_device_options()
    # print("Options: {}".format(pretty_response(ricoh_options)))
