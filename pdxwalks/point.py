from .utils import *

class Point:
    def __init__(self, x, y, elev=None):
        """
        Class that stores x and y indices of points

        Parameters
        ----------
        x: horizontal index (measured from right side of image)
        y: vertical index (measured from top of image)
        elev: elevation (m)
        """

        # x and y represent horizontal and vertical indices of center
        self.x = x
        self.y = y
        self.elev = elev

        # track all indices associated with this point
        self.all_indices = [[self.x, self.y]]

        # track center indices
        self.center_indices = []

    def __repr__(self):
        return f"({self.x}, {self.y})"

    def add_fill_circle(self, dim, center=0):
        """
        Fills out pixels around center in a circle pattern

        Parameters
        ----------
        dim: dimension, radius of circle
        center: radius of center circle

        Returns
        ---------
        None (sets self.all_indices to resulting array containing circle/square indices)
        """
        
        if dim > 1:
            self.all_indices = circle([self.x, self.y], dim)

        if center > 0:
            self.center_indices = circle([self.x, self.y], center)
        return self

    def add_fill(self, dim, shape="circle"):
        """
        Fills out pixels around center in either a circle or a square pattern

        Parameters
        ----------
        dim: dimension, radius of circle or sidelength of square
        shape: shape to draw ('circle' or 'square')

        Returns
        ---------
        None (sets self.all_indices to resulting array containing circle/square indices)
        """
        
        if dim > 1:
            if shape == "circle":
                self.all_indices = circle([self.x, self.y], dim)
            elif shape == "square":
                self.all_indices = square([self.x, self.y], dim)
            else:
                raise ValueError("Invalid shape used in Point.add_fill")
        return self

    def data_dict(self):
        return {"center": [self.x, self.y], "addl_points": self.all_indices, "center_points": self.center_indices}
