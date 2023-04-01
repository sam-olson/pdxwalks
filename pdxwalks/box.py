from .point import Point

class Box:
    def __init__(self, center, height, asp_ratio):
        """
        Object that represents a box in a 2D matrix

        Parameters
        ----------
        center: Point object representing center of box
        height: height of image (int)
        asp_ratio: aspect ratio (width/height) (float)
        """

        self.center = center
        self.height = height
        self.asp_ratio = asp_ratio
        self.width = int(height * asp_ratio)

        self.top_left = Point(int(self.center.x - (self.width/2)), int(self.center.y - (self.height/2)), elev=None)
        self.bot_right = Point(int(self.center.x + (self.width/2)), int(self.center.y + (self.height/2)), elev=None)

    def crop_to_limits(self, shape):
        """
        Crops the box to fit within a certain shape (centers on nearest point in bigger box)

        Parameters
        ----------
        shape: shape of larger box to bound this box in ([int(width), int(height)])
        """

        min_x = self.top_left.x
        max_x = self.bot_right.x

        min_y = self.top_left.y
        max_y = self.bot_right.y
        
        if self.top_left.x < 0:
            min_x = 0
            max_x = self.width
        elif self.bot_right.x >= shape[0]:
            max_x = shape[0] - 1
            min_x = shape[0] - 1 - self.width

        if self.top_left.y < 0:
            min_y = 0
            max_y = self.height
        elif self.bot_right.y > shape[1]:
            max_y = shape[1] - 1
            min_y = shape[1] - 1 - self.height

        mid_x = int((min_x+max_x)/2)
        mid_y = int((min_y+max_y)/2)

        # now update the class variables...
        self.center = Point(mid_x, mid_y, elev=None)
        self.top_left = Point(min_x, min_y, elev=None)
        self.bot_right = Point(max_x, max_y, elev=None)

        return self

    def extract_box(self, image):
        """
        Extracts and returns submatrix from image matrix

        Parameters
        ---------
        image: image matrix

        Returns
        ---------
        Matrix containing data from own shape
        """
        return image[self.top_left.y:self.bot_right.y, self.top_left.x:self.bot_right.x]
