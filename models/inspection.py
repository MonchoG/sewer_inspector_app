import json
import datetime
# Model class for inspeciton report


class InspectionReport():
    def __init__(self, operator_name=None, inspection_date=None, city=None, street=None,
                 pipe_id=None, manhole_id=None, dimensions=None, shape=None, material=None,
                 image_files=None, video_files=None, ricoh_files=None):
        self.operator_name = operator_name
        self.inspection_date = inspection_date if inspection_date is not None else datetime.date.today().strftime("%d_%m_%y")
        self.city = city
        self.street = street
        self.pipe_id = pipe_id
        self.manhole_id = manhole_id
        self.dimensions = dimensions
        self.shape = shape
        self.material = material
        self.detections = []
        self.image_files = image_files if image_files is not None else []
        self.video_files = video_files if video_files is not None else []
        self.ricoh_files = ricoh_files if ricoh_files is not None else []
        # Build report name from defined properties - cuurent date_month_year hour_minutes_seconds City Street Pipe ID manhole ID
        self.inspection_report_name = "reports/" + datetime.datetime.now().strftime("%d_%m_%Y %H_%M_%S") + \
            "  " + self.city + "_" + self.street + "_" + \
            self.pipe_id + "_" + self.manhole_id

    # append list of detections
    def addDetections(self, detections):
        self.detections = detections

    # append video name/path to report
    def addVideoFiles(self, video_files):
        self.video_files.extend(video_files)

    # append image name/path to report
    def addImageFiles(self, image_files):
        self.image_files.extend(image_files)

    # append ricoh img/video path to the report
    def addRicohFiles(self, ricoh_files):
        self.ricoh_files.extend(ricoh_files)

    # convert to json
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    # Writes inspection file in RIBX...
    # TODO add implementation - crrenttly writes to json file
    def write_inspection_file(self):
        data = json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
        with open('{}.json'.format(self.inspection_report_name), 'w', encoding='utf-8') as f:
            f.write(data)
