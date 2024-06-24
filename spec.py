class Spec:
    def __init__(self, data):
        self.data = data
        bbox = data['bbox']
        self.north = bbox['north']
        self.south = bbox['south']
        self.east = bbox['east']
        self.west = bbox['west']
        self.num_peaks = data['num_peaks']

    def is_in_bbox(self, lon: float, lat: float):
        return self.south <= lat <= self.north and self.west <= lon <= self.east
