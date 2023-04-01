import datetime

from .picture import Picture
from .point import Point
from .utils import *

class Route:
    def __init__(self, route_df, buff, dim=1, shape="circle", min_elev=0, max_elev=1200, pics=[]):
        """
        Class for storing data of walk routes

        Parameters
        ----------
        route_df: pandas DataFrame containing route data in index form (timestamp/x/y/elevation)
        buff: buffer around edge of zoom (number of indices)
        dim: dimension, radius of circle or sidelength of square that represents a single point (default 1)
        shape: shape that represents single point, with dimension radius (default 'circle', valid options are 'circle' or
           'square')
        pics: list of pictures associated with a route (list of filepaths to these images)
        """

        self.route_df = route_df
        self.buff = buff
        self.dim = dim
        self.shape = "circle"
        self.min_elev = min_elev
        self.max_elev = max_elev
        self.pics = [Picture(i) for i in pics]

        self.time = self.route_df["Time"]
        # self.date = datetime.datetime.strptime(self.time[0], "%Y-%m-%d %H:%M:%S")
        self.date = self.time[0].to_pydatetime().replace(tzinfo=None)
        self.x = self.route_df["x"]
        self.y = self.route_df["y"]
        self.elev = self.route_df["Elevation"]
        self.elev_ft = [i*3.28084 for i in self.elev]

        self.top_left_coord = self.route_df["TopLeft"][0]
        self.bot_right_coord = self.route_df["BotRight"][0]
        self.img_shape = self.route_df["ImageShape"][0]

        self.top_left = [min(self.x), min(self.y)]
        self.bot_right = [max(self.x), max(self.y)]

        self.zoom_top_left = [self.top_left[0]-self.dim-buff, self.top_left[1]-self.dim-self.buff]
        self.zoom_bot_right = [self.bot_right[0]+self.dim+self.buff, self.bot_right[1]+self.dim+self.buff]

        self.d_x = self.zoom_bot_right[0] - self.zoom_top_left[0]
        self.d_y = self.zoom_bot_right[1] - self.zoom_top_left[1]

        self.center = [int(self.zoom_top_left[0]+(self.d_x/2)), int(self.zoom_top_left[1]+(self.d_y/2))]

        self.elev_scale = [(i-self.min_elev)/(self.max_elev-self.min_elev) for i in self.elev_ft]


        if shape == "circle":
            self.all_indices = [Point(i,j,k).add_fill_circle(dim, 9).data_dict() for i,j,k in zip(self.x, self.y, self.elev)]

        if self.pics:
            self.address_pics()

    def address_pics(self):
        for i in self.pics:
            # iterate through pictures and find nearest index
            min_delta = 10000
            i.point = find_index((i.lat, i.lon), self.top_left_coord, self.bot_right_coord, self.img_shape)
            for n in range(len(self.x)):
                delta = calculate_distance_index(i.point, [self.x[n], self.y[n]])
                if delta < min_delta:
                    min_delta = delta
                    i.nearest_index = n

        if len(self.pics) > 0:
            self.pics = sorted(self.pics, key=lambda x: x.nearest_index)

 


