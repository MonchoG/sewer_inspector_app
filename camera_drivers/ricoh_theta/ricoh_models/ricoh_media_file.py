import json

# Media file model class
# Parses response from '/osc/commands/execute' list files


class MediaFile:
    def __init__(self, name=None, dateTime=None, fileUrl=None, height=None, width=None, projectionType=None):
        self.name = name
        self.dateTime = dateTime
        self.fileUrl = fileUrl
        self.height = height
        self.width = width
        self.projectionType = projectionType

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)

    # Parse list files response entry and return MediaFile object
    def parse_media_file_response(self, media_file):
        self.name = media_file['name']
        self.dateTime = media_file['dateTimeZone']
        self.fileUrl = media_file['fileUrl']
        self.height = media_file['height']
        self.width = media_file['width']
        self.projectionType = media_file['_projectionType']

        return self
