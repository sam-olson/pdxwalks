from .utils import *

class Picture:
    def __init__(self, fpath):
        self.fpath = fpath
        self.matrix = cv2.imread(fpath)
        self.lat, self.lon = image_extract_coords(fpath)
        self.date = image_extract_date(fpath)
        self.height = self.matrix.shape[0]
        self.width = self.matrix.shape[1]
        self.asp_ratio = self.width/self.height

        self.point = None
        self.nearest_index = None
