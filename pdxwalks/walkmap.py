import copy
import json
import sys

import cv2

from .box import Box
from .point import Point
from .route import Route
from .utils import *

class WalkMap:
    def __init__(self, img, top_left, bot_right):
        self.image = img
        self.top_left = top_left
        self.bot_right = bot_right
        self.shape = img.shape
        self.center = [int(self.shape[1]/2), int(self.shape[0]/2)]
        self.asp_ratio = self.shape[1]/self.shape[0]
        self.box = Box(Point(*self.center, elev=None), self.shape[0]-10, self.asp_ratio)

        # frames of final video
        self.vid_frames = []

        # for tracking current image
        self.sub_box = self.box

        # calculating distance per pixel
        self.x_delta = (self.bot_right[1] - self.top_left[1]) / self.shape[1]
        self.y_delta = (self.bot_right[0] - self.top_left[0]) / self.shape[0]

        self.dist_per_pixel_x = calculate_distance_coord(self.top_left, (self.top_left[0], self.top_left[1] + self.x_delta))
        self.dist_per_pixel_y = calculate_distance_coord(self.top_left, (self.top_left[0] + self.y_delta, self.top_left[1]))

        self.dist_per_pixel_avg = np.mean([self.dist_per_pixel_x, self.dist_per_pixel_y])

    def add_pixel(self, x, y, color, add=True):
        """
        Safe way to add a pixel to the image (checks bounds before attempting to reference)

        Parameters
        ----------
        x: horizontal index
        y: vertical index
        color: color of point (length 3 iterable, BGR)
        add: whether or not to add the point to the map (default True)

        Returns
        ----------
        True if pixel successfully added, False if not
        """

        if (x < self.shape[1]) and (x > 0) and (y < self.shape[0]) and (y > 0):
            if add:
                self.image[y][x] = color
            return True
        return False

    def draw_nbhd(self, nbhd_df, size=1, color=[0,0,255]):
        """
        Draws neighborhood outline onto image

        Parameters
        ----------
        nbhd_df: pandas DataFrame containing lats and lons of neighborhood
          vertices
        size: thickness of border in pixels (defaults to 1 pixel)
        color: color of border in CV2 format (BGR) - defaults to red
        """

        lons = nbhd_df["Longitude"]
        lats = nbhd_df["Latitude"]
        vertices = []

        for i,j in zip(lons, lats):
            vertices.append(find_index([j,i], self.top_left, self.bot_right, self.shape))

        interp = []
        for k in range(len(vertices)-1):
            interp += interpolate(vertices[k], vertices[k+1])

        if size > 1:
            interp_square = [square(i, size) for i in interp]
            for m in interp_square:
                for n in m:
                    # self.image[n[1]][n[0]] = color
                    self.add_pixel(n[0], n[1], color)

        else:
            for l in interp:
                # self.image[l[1]][l[0]] = color
                self.add_pixel(l[0], l[1], color)

    def draw_route_discover(self, route, discover_map):
        """
        Adds a route to the image in "discover" mode

        Parameters
        ----------
        route: route object containing data about route
        discover_map: map to fill in "discovered" areas

        Returns
        ----------
        self (updates self.image)
        """
        for i in route.all_indices:
            for j in i["addl_points"]:
                self.image[j[1]][j[0]] = discover_map[j[1]][j[0]]

        return self
         

    def draw_streets(self, fname, color=[255,0,255]):
        """
        Interpolates and draws streets. Input should be JSON file with structure street_name.segments
        
        Parameters
        ----------
        fname: file name/path to JSON file to load
        """
        with open(fname, "r") as f:
            data = json.load(f)

        a = 0

        for k,v in data.items():
            a += 1
            print(f"{a}/{len(data.items())}", k)
            quad = k.split(" ")[0]

            if quad == "N":
                color = [255,0,0]
            elif quad == "NW":
                color = [0,255,0]
            elif quad == "NE":
                color = [0,0,255]
            elif quad == "S":
                color = [255,255,0]
            elif quad == "SW":
                color = [255,0,255]
            elif quad == "SE":
                color = [0,255,255]
            else:
                color = [255,255,255]

            for segment in v["segments"]:
                interp = []
                for n in range(len(segment)-1):
                    start = segment[n]
                    end = segment[n+1]
                    if n == 0:
                        start_index = find_index([start[1], start[0]], self.top_left, self.bot_right, self.shape)
                    else:
                        start_index = end_index

                    end_index = find_index([end[1], end[0]], self.top_left, self.bot_right, self.shape)

                    interp += interpolate(start_index, end_index)

                for i in interp:
                    self.add_pixel(i[0], i[1], color)

    def draw_distance_text(self, img, dist, unit="mi", x_buff=0.05, y_buff=0.1):
        """
        Draws distance travelled onto the image

        Parameters
        ----------
        img: image on which to draw
        dist: current distance
        unit: unit of measurement for distance
        x_buff: horizontal buffer from left of screen (final distance in pixels from left of image is the width of image * x_buff)
        y_buff: vertical buffer from bottom of screen (final distance in pixels from top of image is the height of image * y_buff)
        """
        draw_text(img, f"{'%.3f'%round(dist,3)} {unit}", (int(img.shape[1]*x_buff), int(img.shape[0]*y_buff)))

    def draw_elev_profile(self, img, index, elev_indices, route, y_span=50, x_buff=0.05, y_buff=0.9, rad=1, color=[0,255,0], bg=[0,0,0], text=True):
        """
        Draws profile of elevation of route onto the image

        Parameters
        ----------
        img: image on which to draw
        index: index of current elevation point
        elev_indices: list of previous elevation indices (for drawing the historical line)
        route: route object representing route being plotted
        y_span: number of pixels of y span of the elevation profile (should be integer, default is 50)
        x_buff: horizontal buffer as percentage of image width from left of image (default is 0.05)
        y_buff: vertical buffer as percentage of image height from bottom of image (default is 0.8)
        rad: radius of point being drawn (default is 1 pixel)
        color: color of point being draw (default is green)
        bg: background color (default is black)
        text: toggle whether or not to display elevation as text as well

        Returns
        ----------
        None (draws on passed image)
        """

        x_span = int(img.shape[1]-(2*x_buff*img.shape[1]))
        x_ind_min = int(img.shape[1]*x_buff)
        x_ind_max = x_ind_min + x_span
        x_index = int((index/len(route.elev))*x_span) + int(x_buff*img.shape[1])

        y_min = np.min(route.elev_ft)
        y_max = np.max(route.elev_ft)
        curr_elev = route.elev_ft[index]

        y_ind_min = int(img.shape[0]*y_buff) - y_span
        y_ind_max = int(img.shape[0]*y_buff)
        y_index = int(img.shape[0]*y_buff) - int(((curr_elev-y_min)/(y_max-y_min)) * y_span)

        elev_indices.append([x_index, y_index])

        if bg:
            for x in range(x_ind_min, x_ind_max):
                for y in range(y_ind_min, y_ind_max):
                    try:
                        img[y][x] = bg
                    except:
                        continue
        
        for i in elev_indices:
            c = circle([i[0], i[1]], rad)
            for j in c:
                img[j[1]][j[0]] = color

        if text:
            draw_text(img, f"{round(curr_elev,1)}'", (x_index, y_index),
                    font=cv2.FONT_HERSHEY_PLAIN,
                    font_scale=1,
                    font_thickness=1,
                    text_color=(255,255,255),
                    text_color_bg=(0,0,0),
                    padding=(5, 5))

    def draw_elev_bar(self, img, index, route, 
            elev_bar_x_offset=10, 
            height_pct=0.3, 
            elev_bar_asp_ratio=0.1, 
            bar_col=(255,255,255), 
            track_col=(255,0,0)):
        """
        Draws elevation tracker bar onto image

        Parameters
        ----------
        img: image on which to draw
        index: index of current elevation
        route: route containing elevation data (Route object)
        elev_bar_x_offset: how many pixels form the left of the image edge to place the bar (default 10px)
        height_pct: ratio of height of tracker bar to final image (default 0.3)
        elev_bar_asp_ratio: aspect ratio of the tracker bar (default 0.1)
        bar_col: background color of the bar (default white)
        track_col: color of live tracker (default blue)

        Returns
        ----------
        None (draws on passed image)
        """

        img_height = img.shape[0]

        # defining height and width of elevation bar
        elev_bar_height = int(img_height*height_pct)
        elev_bar_width = int(elev_bar_asp_ratio*elev_bar_height)

        # defining top left and bottom right corner locations of elevation bar
        elev_bar_top_left = (elev_bar_x_offset, int((img_height-elev_bar_height)/2))
        elev_bar_bot_right = (elev_bar_x_offset+elev_bar_width, int((img_height-elev_bar_height)/2)+elev_bar_height)

        # defining height and width of live tracker
        elev_track_width = elev_bar_width
        elev_track_height = int(0.15*elev_bar_width)

        # drawing elevation bar and live tracker on image
        cv2.rectangle(img, elev_bar_top_left, elev_bar_bot_right, bar_col, -1)
        elev_track_top_left = (elev_bar_x_offset, int((elev_bar_height*(1-route.elev_scale[index]))+elev_bar_top_left[1]-elev_track_height))
        elev_track_bot_right = (elev_bar_x_offset+elev_track_width, int((elev_bar_height*(1-route.elev_scale[index]))+elev_bar_top_left[1]))
        cv2.rectangle(img, elev_track_top_left, elev_track_bot_right, track_col, -1)

        # adding text to image
        draw_text(img, f"{round(route.elev_ft[index],1)}'", (elev_bar_x_offset+elev_track_width+10, int((elev_bar_height*(1-route.elev_scale[index]))+elev_bar_top_left[1]-(elev_track_height/2))), font=cv2.FONT_HERSHEY_PLAIN)

    def zoom_and_pan(self, start, end, steps, final_height):
        """
        Creates zoom and pan pattern in matrix

        Parameters
        ----------
        start: starting point (as Box object)
        end: ending point (as Box object)
        steps: number of steps in which to zoom and pan (int)

        Returns
        ----------
        Array of matrices representing slices of image zoomed/panned
        """

        # define where the centers of your squares will go
        center_pattern = evenly_spaced_points_to(start.center, end.center, steps)

        delta = (end.height-start.height)/(steps-1)
        sizes = [int(i) for i in np.arange(start.height, end.height+delta, delta)]

        images = []
        final_width = int(self.asp_ratio * final_height)

        for i,j in zip(center_pattern, sizes):
            # create a box for each point
            self.sub_box = Box(i, j, self.asp_ratio)
            self.sub_box.crop_to_limits(list(reversed(list(self.shape[:2]))))
            images.append(self.sub_box.extract_box(self.image))

        resized_imgs = []

        for n, i in enumerate(images):
            resized_imgs.append(cv2.resize(i, [final_width, final_height], interpolation=cv2.INTER_AREA))

        return resized_imgs

    def add_pic_zoom(self, pic, bg_img, h_0, save_h, step=100, h_f="height", dwell_f=50):
        """
        Adds a picture by zooming it in on map

        Parameters
        ----------
        pic: picture to add (Picture object)
        bg_img: background image (numpy matrix)
        h_0: initial height of image
        save_h: height of saved image
        step: number of pixels to increase height by on each frame
        h_f: final height of image (default 'height' for height of map)
        dwell_f: number of frames to dwell on the expanded image (default 50)

        Returns
        ----------
        None (adds frames to self.vid_frames)
        """

        # TODO: add error handling for pictures that may display outside the bounding box
        forward_imgs = []

        if h_f == "height":
            h_f = self.shape[0]

        for h in range(h_0, h_f, step):
            w = int(h * pic.asp_ratio)
            resized_pic = cv2.resize(copy.deepcopy(pic.matrix), [w, h], interpolation=cv2.INTER_AREA)
            top_left = [int(pic.point[0]-w/2), int(pic.point[1]-h/2)]
            bot_right = [int(pic.point[0]+w/2), int(pic.point[1]+h/2)]

            # if the picture zoom ends up hitting the boundary of the background image, cut it off early
            try:
                bg_img[top_left[1]:bot_right[1], top_left[0]:bot_right[0]] = resized_pic
            except IndexError as e:
                print(e)
                print(f"Stopping picture zoom at height {h}!")
                break

            save_img = cv2.resize(self.sub_box.extract_box(bg_img), [int(save_h*self.asp_ratio), save_h], interpolation=cv2.INTER_AREA)

            forward_imgs.append(save_img)
        
        # expanding frames
        self.vid_frames += forward_imgs

        # dwell on final expanded frame for given number of frames
        self.vid_frames += [forward_imgs[-1]]*dwell_f

        # reverse expand frames
        self.vid_frames += forward_imgs[::-1]
            
    def snake_path_discover(self, 
            routes, 
            discover_map, 
            save_path,
            marker_col=[255,0,0], 
            skip_level=5, 
            final_height=500,
            dwell_f=50,
            fps=30,
            clear_marker=True,
            distance=None,
            elev=None):
        """
        Creates a snake path that "discovers" (i.e., borrows pixels from) another map.
          Essentially simulates discovering new areas in a video game map

        Parameters
        ----------
        routes: routes to plot (list of Route objects)
        discover_map: image representing map that data is "discovered" from (should be same size as self.image)
        save_path: path to save video to
        marker_col: color of marker representing center of discover area
        skip_level: frequency of image capture (i.e., every 5 points)
        final_height: height of final video (width calculated from aspect ratio)
        dwell_f: number of frames to dwell on final map image (default 50)
        clear_marker: if true, will clear marker after frame is captured (boolean)
        distance: if not None, will track and display distance traveled, can pass kw arguments as dictionary
        elev: if not None, will track and display elevation on a sliding scale, can pass kw arguments as dictionary

        Returns
        ----------
        List of matrices representing frames to be made into a video/gif
        """

        current_box = self.box

        for route in routes:
            # determine zoom box
            zoom_box_height = route.d_y
            if route.d_x > route.d_y:
                zoom_box_height = int(route.d_x/self.asp_ratio)
            elif route.d_x <= route.d_y:
                zoom_box_width = int(route.d_y*self.asp_ratio)

            # list for tracking elevation indices
            elev_indices = []

            zoom_box = Box(Point(*route.center, elev=None), zoom_box_height, self.asp_ratio).crop_to_limits([self.shape[1], self.shape[0]])

            # zoom in
            self.vid_frames += self.zoom_and_pan(current_box, zoom_box, 100, final_height)
            current_box = zoom_box

            # tracking distance
            tot_distance = 0

            # elevation tracker bar dimensions
            elev_bar_x_offset = 10
            elev_bar_height = int(0.333*final_height)
            elev_bar_asp_ratio = 0.1
            elev_bar_width = int(elev_bar_asp_ratio*elev_bar_height)
            elev_bar_top_left = (elev_bar_x_offset, int(final_height*0.333))
            elev_bar_bot_right = (elev_bar_x_offset+elev_bar_width, int(final_height*0.333)+elev_bar_height)

            # dimensions of live elevation
            elev_track_width = elev_bar_width
            elev_track_height = int(0.15*elev_bar_width)

            # pictures that go with the route
            route_pics = copy.copy(route.pics)

            # run snake
            for a,i in enumerate(route.all_indices):
                add_pic = False
                skip = False

                if a > 0:
                    tot_distance += calculate_distance_index(i["center"], route.all_indices[a-1]["center"]) * self.dist_per_pixel_avg
                for j in i["addl_points"]:
                    if not self.add_pixel(*j, [0,0,0], add=False):
                        skip = True
                        continue
                    self.image[j[1]][j[0]] = discover_map[j[1]][j[0]]
                for k in i["center_points"]:
                    if not self.add_pixel(*k, [0,0,0], add=False):
                        skip = True
                        continue
                    self.image[k[1]][k[0]] = marker_col

                # clear marker from previous frame
                if clear_marker and (not skip):
                    if a > 0:
                        for p in route.all_indices[a-1]["center_points"]:
                            self.image[p[1]][p[0]] = discover_map[p[1]][p[0]]

                if len(route_pics) > 0:
                    if a > route_pics[0].nearest_index:
                        add_pic = True

                # save the image
                if a%skip_level == 0:
                    save_img = cv2.resize(copy.deepcopy(self.sub_box.extract_box(self.image)), [int(final_height*self.asp_ratio), final_height], interpolation=cv2.INTER_AREA)
                    if distance:
                        self.draw_distance_text(save_img, tot_distance, **distance)
                    if elev:
                        if elev["type"] == "bar":
                            self.draw_elev_bar(save_img, a, route, **elev["kws"])
                        elif elev["type"] == "prof":
                            self.draw_elev_profile(save_img, a, elev_indices, route, **elev["kws"])
                    if add_pic:
                        f = route_pics.pop(0)
                        self.add_pic_zoom(f, copy.deepcopy(self.image), 10, final_height, step=50, h_f=1000)
                        add_pic = False

                    self.vid_frames.append(save_img)

            if clear_marker:
                for i in route.all_indices[a]["center_points"]:
                    if not self.add_pixel(*i, [0,0,0], add=False):
                        continue
                    self.image[i[1]][i[0]] = discover_map[i[1]][i[0]]

            save_img = cv2.resize(copy.deepcopy(self.sub_box.extract_box(self.image)), [int(final_height*self.asp_ratio), final_height], interpolation=cv2.INTER_AREA)
            if distance:
                self.draw_distance_text(save_img, tot_distance, **distance)
            if elev:
                if elev["type"] == "bar":
                    self.draw_elev_bar(save_img, a, route, **elev["kws"])
                elif elev["type"] == "prof":
                        self.draw_elev_profile(save_img, a, elev_indices, route, **elev["kws"])

            self.vid_frames.append(save_img)
            self.vid_frames += [self.vid_frames[-1]] * dwell_f

        self.vid_frames += self.zoom_and_pan(current_box, self.box, 100, final_height)
        write_video(self.vid_frames, save_path, fps=fps)



