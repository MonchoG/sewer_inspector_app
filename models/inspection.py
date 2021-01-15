import json

# Model class for inspeciton report
class InspectionReport():
    def __init__(self, operator_name=None, inspection_date=None, city=None, street=None, pipe_id=None, manhole_id=None, dimensions=None, shape=None, material=None):
        self.operator_name = operator_name
        self.inspection_date = inspection_date
        self.city = city
        self.street = street
        self.pipe_id = pipe_id
        self.manhole_id = manhole_id
        self.dimensions = dimensions
        self.shape = shape
        self.material = material
        self.detections = []

    # append list of detections
    def addDetections(self, detections):
        self.detections = detections

    # convert to json
    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    # Writes inspection file in RIBX...
    # TODO add implementation - crrenttly writes to json file
    def write_inspection_file(self, name='default_name'):
        data = json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)
        with open('{}.json'.format(name), 'w', encoding='utf-8') as f:
            f.write(data)
