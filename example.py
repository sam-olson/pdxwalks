import cv2
import os

from pdxwalks.route import Route
from pdxwalks.utils import convert_latlon_to_index, gpx_to_dataframe, timestamp
from pdxwalks.walkmap import WalkMap

# define top left and bottom right coordinates (latitude, longitude)
TOP_LEFT = (45.6065, -122.8138)
BOT_RIGHT = (45.4535, -122.5462)

# load the foreground image
FOREGROUND_IMG = cv2.imread("./source_maps/nbhd_street_test_walk.png")

# load the background image
BACKGROUND_IMG = cv2.imread("./source_maps/full_image.png")

# create the WalkMap object
WMAP = WalkMap(FOREGROUND_IMG, TOP_LEFT, BOT_RIGHT)

# load the GPS data and convert it to indices based on the map coordinates 
route_data = convert_latlon_to_index(gpx_to_dataframe("./example_routes/2023-01-16-153108.gpx"), TOP_LEFT, BOT_RIGHT, WMAP.shape)

# select pictures to be added to the animation
pics = [f"./example_images/{i}" for i in os.listdir("./example_images") if i.endswith(".jpeg")]

# create the Route object, with zoom buffer of 500 pixels and discovery radius of 30 pixels
route = Route(route_data, buff=500, dim=30, pics=pics)

# define parameters for distance tracker
dist_params = {"unit": "mi", 
        "x_buff": 0.05, 
        "y_buff": 0.1}

# define parameters for elevation tracker
elev_params = {"type": "prof", "kws": {"y_span": 100,
    "x_buff": 0.05,
    "y_buff": 0.9,
    "rad": 3,
    "color": [0,255,0],
    "bg": [0,0,0],
    "text": True}}

# define the file name of the output video
tstamp = timestamp()

# create the snake path animation
WMAP.snake_path_discover(routes=[route], 
        discover_map=BACKGROUND_IMG, 
        save_path=f"{tstamp}.mp4", 
        distance=dist_params, 
        elev=elev_params, 
        skip_level=2, 
        final_height=1000) 


# uncomment the line below if you wish to run FFMPEG compression automatically
# os.system(f"ffmpeg -i {tstamp}.mp4 -vcodec libx264 -pix_fmt yuv420p -crf 30 {tstamp}_compressed.mp4")
