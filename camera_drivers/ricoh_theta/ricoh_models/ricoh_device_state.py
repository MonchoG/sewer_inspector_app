import json


class RicohState:
    def __init__(self, battery_level, captureStatus, storage_left, capture_mode, fileFormat, remaning_video_seconds):
        self.battery_level = battery_level
        self.captureStatus = captureStatus

        self.storage_left = storage_left
        self.capture_mode = capture_mode
        self.fileFormat = fileFormat
        self.remaning_video_seconds = remaning_video_seconds

    def update_state(self, battery_level=None, captureStatus=None, storage_left=None, capture_mode=None, fileFormat=None, remaning_video_seconds=None):
        if battery_level:
            self.battery_level = battery_level
        if captureStatus:
            self.captureStatus = captureStatus
        if storage_left:
            self.storage_left = int(storage_left)
        if capture_mode:
            self.capture_mode = capture_mode
        if fileFormat:
            self.fileFormat = fileFormat
        if remaning_video_seconds:
            self.remaning_video_seconds = remaning_video_seconds
        return self

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
