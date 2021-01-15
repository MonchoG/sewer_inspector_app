class RicohState:
    def __init__(self, battery_level, storage_left, capture_mode, fileFormat, remaning_video_seconds):
        self.battery_level = battery_level
        self.storage_left = storage_left
        self.capture_mode = capture_mode
        self.fileFormat = fileFormat
        self.remaning_video_seconds = remaning_video_seconds

    def update_state(self, battery_level=None, storage_left=None, capture_mode=None, fileFormat=None, remaning_video_seconds=None):
        if battery_level:
            self.battery_level = battery_level
        if storage_left:
            self.storage_left = storage_left
        if capture_mode:
            self.capture_mode = capture_mode
        if fileFormat:
            self.fileFormat = fileFormat
        if remaning_video_seconds:
            self.remaning_video_seconds = remaning_video_seconds
        return self
