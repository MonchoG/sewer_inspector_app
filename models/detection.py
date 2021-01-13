import json

# Model class for detection
# type - the detection label
# location - distance from reference point
# distance - distance to detected object
# time from start - timestamp of the inspewction when the object was detected
class Detection:
    def __init__(self, damage_type=None, location=None, distance=None, time_from_start=None):
        self.type = damage_type
        self.location = location
        self.distance = distance
        self.time_from_start = time_from_start

    def print_detection(self):
        print("Detection {} at {} m from start  {} m far away from camera".format(
            self.type, self.location, self.distance))

    def set_time(self, time_string):
        self.time_from_start = time_string

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                        sort_keys=True, indent=4)
