import datetime
import itertools
import random

import cv2
from GPSPhoto import gpsphoto
import gpxpy
import numpy as np
import pandas as pd
from PIL import Image

from .config import *

### imported in evenly_space_points_to below to avoid circular imports
# from .point import Point

def timestamp():
    """
    Creates a timestamp at current moment
    """

    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def calculate_distance_index(point_1, point_2):
    """
    Calculates number of pixels between two point objects

    Parameters
    ----------
    point_1: first point [x,y]
    point_2: second point [x,y] 

    Returns
    ----------
    Distance (in pixels) between two points
    """

    return np.sqrt(pow(point_1[0]-point_2[0], 2) + pow(point_1[1]-point_2[1], 2))

def haversine(l_1, l_2):
    """
    Calculates haversine of angle

    Parameters
    ----------
    l_1: latitude or longitude of first point (in radians)
    l_2: latitude or longitude of second point (in radians)

    Returns
    ----------
    haversine of angle (float)
    """

    return (1 - (np.cos(l_2 - l_1))) / 2.0

def calculate_distance_coord(point_1, point_2, units="mi"):
    """
    Calculates distance between two points

    Parameters
    ----------
    point_1: first point, should be [lat, lon]
    point_2: second point, should be [lat, lon]
    units: units answer provided in (mi/km/m)

    Returns
    ----------
    distance between the points in specified units (float)
    """

    point_1 = [np.radians(i) for i in point_1]
    point_2 = [np.radians(i) for i in point_2]


    return 2 * RAD_EARTH * DIST_UNITS[units] * np.arcsin(np.sqrt(haversine(point_1[0], point_2[0]) + np.cos(point_1[0]) * np.cos(point_2[0]) * haversine(point_1[1], point_2[1])))

def find_index(point, top_left, bot_right, img_shape):
    """
    Finds index of a given coordinate in an image array

    Parameters
    ----------
    point: lat/lon of point of interest as a 2-element array
    top_left: lat/lon of top left corner of displayed map as 2-element array
    bot_right: lat/lon of bottom right corner of displayed map as a 2-element array
    img_shape: dimension of image in format [height, width]

    Returns
    ----------
    Horizontal and vertical indices as 2-element array
    """
    
    # extract image width and height from shape
    img_w = img_shape[1]
    img_h = img_shape[0]

    # determine span of image in lat/lon
    img_span_w = bot_right[1] - top_left[1]
    img_span_h = top_left[0] - bot_right[0]

    # determine horizontal and vertical "steps"
    hor_step = img_span_w/img_w
    ver_step = img_span_h/img_h

    # calculate indices
    hor_index = int((point[1] - top_left[1]) / hor_step)
    ver_index = int((top_left[0] - point[0]) / ver_step)
    
    return (hor_index, ver_index)

def image_extract_coords(img_path):
    """
    Extracts latitude and longitude from image EXIF data

    Parameters
    ----------
    img_path: filepath of image

    Returns
    ----------
    Tuple containing coordinates (lat, lon)
    """

    exif_data = gpsphoto.getGPSData(img_path)

    return exif_data["Latitude"], exif_data["Longitude"]

def image_extract_date(img_path):
    """
    Extracts date and time from image EXIF data

    Parameters
    ----------
    img_path: filepath of image

    Returns
    ----------
    Tuple containing date and time
    """

    data = Image.open(img_path)._getexif()[36867]
    return datetime.datetime.strptime(data, "%Y:%m:%d %H:%M:%S")

def within_x_hours(time_1, time_2, hrs=3):
    """
    Determines whether two times are within a given number of hours of one another

    Parameters
    ----------
    time_1: datetime object
    time_2: datetime object
    hrs: number of hours to check (default 3)

    Returns
    ----------
    True (if times are within x hours) or False (if times are not within x hours)
    """

    delta = abs(time_1-time_2)

    if (delta.days == 0) and (delta.seconds <= (hrs*3600)):
        return True
    else:
        return False

def circle(center, radius):
    """
    Provides indices of circle with given radius and center

    Parameters
    ----------
    center: center point of circle (array of length 2)
    radius: radius of circle (integer)

    Returns
    ----------
    List of length-2 arrays containing indices of circle
    """

    # need to convert numpy array to a list for JSON serialization
    side = np.arange(-radius, radius+1, dtype=int).tolist()

    # perform element-wise product to get combination of all 
    #  indices in a square with side length 2*radius
    square = list(itertools.product(side,side))

    # filter for coordinates in square that fall within circle of given radius
    coords = [[center[0]+i[0], center[1]+i[1]] for i in square if np.sqrt(pow(i[0],2)+pow(i[1],2)) < radius]

    return coords

def square(center, side_l):
    """
    Provides indices of square with given side length and center


    Parameters
    ----------
    center: center point of square
    side_l: length of side (should be an odd number)

    Returns
    ----------
    List of 2 element arrays containing indices of square
    """

    if side_l % 2 == 0:
        side_l -= 1

    if side_l == 1:
        return [center]
    else:
        ends = (side_l-1) / 2

        # need to convert numpy arrays to lists for JSON serialization
        hor_indices = np.arange(int(center[0]-ends), int(center[0]+ends+1), dtype=int).tolist()
        ver_indices = np.arange(int(center[1]-ends), int(center[1]+ends+1), dtype=int).tolist()
        return list(itertools.product(hor_indices, ver_indices))

def interpolate(start, end):
    """
    Draws a 'straight' line between a start point and an end point (assuming indices)

    Parameters
    ----------
    start: start point indices (2 element array)
    end: end point indices (2 element array)

    Return
    ----------
    list containing indices of all points of straight line between start and end
    """

    # calculate deltas
    d_x = end[0] - start[0]
    d_y = end[1] - start[1]

    x_s = []
    y_s = []

    if d_x != 0:
        ang = np.arctan(d_y/d_x)
    else:
        ang = np.pi

    # for angles < 45deg
    if abs(d_x) >= abs(d_y):
        # length of return array is determined by d_x
        if d_x < 0:
            x_s = list(range(start[0], end[0]-1, -1))
        elif d_x > 0:
            x_s = list(range(start[0], end[0]+1))
        else:
            x_s = []

        # calculating y_s
        y_s = [int((i-start[0])*np.tan(ang))+start[1] for i in x_s]
    
    else:
        # length of return array is determined by d_y
        if d_y < 0:
            y_s = list(range(start[1], end[1]-1, -1))
        elif d_y > 0:
            y_s = list(range(start[1], end[1]+1))
        else:
            y_s = []

        # calculating x_s
        if ang == np.pi:
            x_s = [start[0] for i in y_s]
        else:
            x_s = [int((i-start[1])/np.tan(ang))+start[0] for i in y_s]
    
    return list(zip(x_s, y_s))

def evenly_spaced_points_to(from_point, to_point, quant):
    """
    Provides coordinates of evenly spaced points on path to given point

    Parameters
    ----------
    from_point: where you want to start (Point object)
    to_point: where you want to end up (Point object)
    quant: number of points on the line (int)

    Returns
    ----------
    Array of Point objects representing evenly spaced points on a line between two points
    """

    # avoiding circular imports...
    from .point import Point
    points = np.linspace([from_point.x, from_point.y], [to_point.x, to_point.y], num=quant)

    return [Point(int(i[0]), int(i[1]), elev=None) for i in points]

def gpx_to_dataframe(file_name, time_delta=-7):
    """
    Converts a GPX file to a pandas dataframe

    Parameters
    ----------
    file_name: path/file name of GPX file
    time_delta: difference in hours between your timezone and UTC (-7 is PST)

    Returns
    ----------
    pandas dataframe containing time/longitude/latitude data
    """

    with open(file_name) as f:
        gpx_file_data = gpxpy.parse(f)

    times = []
    longitudes = []
    latitudes = []
    elevations = []

    for track in gpx_file_data.tracks:
        for segment in track.segments:
            for point in segment.points:
                point.adjust_time(datetime.timedelta(hours=time_delta))
                times.append(point.time)
                longitudes.append(point.longitude)
                latitudes.append(point.latitude)
                elevations.append(point.elevation)

    return pd.DataFrame(data={"Time": times, "Longitude": longitudes, "Latitude": latitudes, "Elevation": elevations})

def nbhd_to_dataframe(file_name):
    """
    Loads data from text files that contain neighborhood vertex coordinates

    Parameters
    ----------
    file_name: path/file name of .txt file

    Returns
    ----------
    pandas dataframe containing lats and lons of neighborhood vertices
    """

    data = np.loadtxt(file_name)
    
    longitudes = []
    latitudes = []
    for i in data:
        longitudes.append(i[0])
        latitudes.append(i[1])

    return pd.DataFrame(data={"Longitude": longitudes, "Latitude": latitudes})

def random_color():
    """
    Returns a length 3 list with random values between 0-255 representing a random color
    """
    return [random.randint(0,255) for i in range(3)]

def create_zoom_box(center, size, img_shape):
    """
    Create a box in an image of a given size

    Parameters
    ----------
    center: indices to center the box on [x,y]
    size: size of box [width,height]
    img_shape: shape of original image (for boundary issues) [width,height]

    Returns
    ----------
    Boundaries of zoomed box
    """
    edge_x = int(size[0]/2)
    edge_y = int(size[1]/2)

    left_x = center[0] - edge_x
    right_x = center[0] + edge_x

    if left_x < 0:
        left_x = 0
        right_x = size[0]
    elif right_x >= img_shape[0]:
        left_x = img_shape[0] - 1 - size[0]
        right_x = img_shape[0] - 1

    top_y = center[1] - edge_y
    bot_y = center[1] + edge_y

    if top_y < 0:
        top_y = 0
        bot_y = size[1]
    elif bot_y >= img_shape[1]:
        top_y = img_shape[1] - 1 - size[1]
        bot_y = img_shape[1] - 1

    return [[int(left_x), int(top_y)], [int(right_x), int(bot_y)]]

def image_zoom(img, center, mag=2, step=0.005):
    img_size = img.shape[:2]
    factor = 0.05
    final_img_size = [int(i*factor) for i in img_size]

    cv2.imwrite(f"scale/test_scale_{str(1).zfill(4)}.png", img)

    for n, i in enumerate(np.arange(2, mag, step)):
        new_size = [int(img_size[1]/i), int(img_size[0]/i)]
        # img_2 = img[:new_size[1], :new_size[0]]
        ind = create_zoom_box(center, new_size, img_size)
        img_2 = img[ind[0][1]:ind[1][1], ind[0][0]:ind[1][0]]
        # img_2 = cv2.resize(img_2, [img_size[1], img_size[0]], interpolation=cv2.INTER_LINEAR)
        img_2 = cv2.resize(img_2, [final_img_size[1], final_img_size[0]], interpolation=cv2.INTER_AREA)
        cv2.imwrite(f"scale/test_scale_{str(n).zfill(4)}.png", img_2)

def write_video(imgs, path, fps=15):
    """
    Writes .mp4 video from array of image matrices

    Parameters
    ----------
    imgs: array of image matrices
    path: path to which you want to save the video

    Returns
    ----------
    None (saves video)
    """

    height,width,layers = imgs[0].shape
    fourcc = cv2.VideoWriter_fourcc("m", "p", "4", "v")
    writer = cv2.VideoWriter(path, fourcc, fps, (width, height))

    for i in imgs:
        writer.write(i)

    writer.release()
    cv2.destroyAllWindows()

def convert_latlon_to_index(latlon_df, top_left, bot_right, img_shape, save_path=False):
    """
    Converts a file with latitudes and longitudes into a file with indices for a given map

    Parameters
    ----------
    latlon_file: pandas DataFrame containing lats and lons as returned by gpx_to_dataframe
    top_left: lat/lon of top left corner of displayed map as 2-element array
    bot_right: lat/lon of bottom right corner of displayed map as a 2-element array
    img_shape: dimension of image in format [height, width]
    save_path: path to save index file to

    Returns
    ----------
    Returns pandas DataFrame containing x and y index data
    """
    
    x_indices = []
    y_indices = []

    for i,j in zip(latlon_df["Latitude"], latlon_df["Longitude"]):
        indices = find_index((i,j), top_left, bot_right, img_shape)
        x_indices.append(indices[0])
        y_indices.append(indices[1])

    top_left_lst = [top_left for i in range(len(x_indices))]
    bot_right_lst = [bot_right for i in range(len(x_indices))]
    img_shape_lst = [img_shape for i in range(len(x_indices))]
    retdf = pd.DataFrame(data={"Time": latlon_df["Time"], 
        "x": x_indices, 
        "y": y_indices, 
        "Elevation": latlon_df["Elevation"],
        "TopLeft": top_left_lst,
        "BotRight": bot_right_lst,
        "ImageShape": img_shape_lst})

    if save_path:
        retdf.to_csv(save_path, index=False)

    return retdf

# below function adapted from: https://stackoverflow.com/questions/60674501/
def draw_text(img, text, pos,
        font=cv2.FONT_HERSHEY_SIMPLEX,
        font_scale=1,
        font_thickness=1,
        text_color=(255,255,255),
        text_color_bg=(0,0,0),
        padding=(5, 5)):
    """
    Puts text on an image with a given background color

    Parameters
    ----------
    img: image on which to put the text (3D array)
    text: text to be put onto the image (string)
    pos: position on the image to place the text (tuple/list with format [x,y])
    font: font of text (cv2 font type)
    font_scale: scale of text (int)
    font_thickness: thickness of font (int)
    text_color: color of text (three element tuple/list)
    text_color_bg: color of background behind text (three element tuple/list)
    padding: padding between box and text in x and y direction (two element tuple/list)

    Returns
    ----------
    Shape of text
    """

    x,y = pos
    text_size,_ = cv2.getTextSize(text, font, font_scale, font_thickness)
    text_w, text_h = text_size
    cv2.rectangle(img, (pos[0]-padding[0], pos[1]-padding[1]), (x+text_w+padding[0], y+text_h+padding[1]), text_color_bg, -1)
    cv2.putText(img, text, (x, y+text_h+font_scale-1), font, font_scale, text_color, font_thickness)

    return text_size


