import asyncio
import json
import os
import threading
import time
import tkinter as tk
from tkinter import filedialog as fd
from tkinter import ttk

import cv2
import pandas as pd

from pdxwalks.config import COLORS
from pdxwalks.picture import Picture
from pdxwalks.route import Route
from pdxwalks.utils import convert_latlon_to_index, gpx_to_dataframe, timestamp, within_x_hours
from pdxwalks.walkmap import WalkMap


def auto_update_entry(entry, value):
    """
    Inserts given value into tkinter Entry object

    Parameters
    ----------
    entry: tk.Entry object 
    value: value to be inserted into 'entry'
    """

    entry.delete(0, tk.END)
    entry.insert(0, value)

class App(tk.Frame):
    def __init__(self, master=None):
        """
        Main GUI class, inherits from tkinter Frame object
        """

        super().__init__(master)

        self.master = master
        self.row_n = 0
        self.elev_track_row_n = 0
        self.dist_track_row_n = 0
        self.vid_param_row_n = 0

        self.selected_gpx = []
        self.selected_gpx_fpaths = []
        self.bg_img = None
        self.bg_img_obj = None
        self.fg_img = None
        self.fg_img_obj = None
        self.top_left = (45.6065, -122.8138)        # coordinates of top left corner (lat, lon)
        self.bot_right = (45.4535, -122.5462)       # coordinates of bottom right corner (lat, lon)
        self.zoom_buff = 500                        # buffer (in pixels) of zoom area
        self.disc_radius = 30                       # radius of 'discovery' circle
        self.disp_pics = []                         # list of pictures to be displayed

        self.ppf = 2                    # points per frame value
        self.dwell_frames = 50          # dwell frames
        self.elev_y_span = 50           # elevation tracker Y span
        self.elev_x_buff = 0.05         # X buffer for elevation tracker
        self.elev_y_buff = 0.90         # Y buffer for elevation tracker
        self.dist_x_buff = 0.05         # X buffer for distance tracker
        self.dist_y_buff = 0.90         # Y buffer for distance tracker
        self.frame_rate = 30            # frame rate
        self.final_height = 500         # final height of video
        self.save_folder_path = os.getcwd() # folder to save output

        self.ffmpeg_command = "ffmpeg -i <file> -vcodec libx264 -pix_fmt yuv420p -crf 30 <out_file>"

        # button background color
        self.button_bg = "#D9DADB"
        
        self.grid(column=0, row=0)

        # starting columns and rows of each sub-frame [col,row]
        self.fi_start = [0,0]   # file input
        self.ap_start = [0,3]   # animation parameters

        self._build_frames()

        try:
            self._load_config("./config_files/last.json")
        except:
            self._load_config("./config_files/default.json")


    def _build_frames(self):
        """
        Method for building out sub-frames
        """
        self.file_input_frame = tk.LabelFrame(self)
        self.file_input_frame.grid(column=self.fi_start[0], row=self.fi_start[1], columnspan=4, rowspan=3, sticky="wens")
        self.file_input_frame.grid_columnconfigure(0, weight=1)
        self.row_n = self._place_file_input_frame(self.row_n)

        self.anim_param_frame = tk.LabelFrame(self)
        self.anim_param_frame.grid(column=0, row=self.row_n, columnspan=4, rowspan=6, sticky="wens")
        self.anim_param_frame.grid_columnconfigure(0, weight=1)
        self.row_n = self._place_anim_param_frame(self.row_n)

        self.elev_param_frame = tk.LabelFrame(self)
        self.elev_param_frame.grid(column=0, row=self.row_n, columnspan=4, rowspan=6, sticky="wens")
        self.elev_param_frame.grid_columnconfigure(0, weight=1)
        self.elev_track_row_n = self.row_n
        self.row_n = self._place_elev_param_frame(self.row_n)

        self.dist_param_frame = tk.LabelFrame(self)
        self.dist_param_frame.grid(column=0, row=self.row_n, columnspan=4, rowspan=3, sticky="wens")
        self.dist_param_frame.grid_columnconfigure(0, weight=1)
        self.dist_track_row_n = self.row_n
        self.row_n = self._place_dist_param_frame(self.row_n)

        self.vid_param_frame = tk.LabelFrame(self)
        self.vid_param_frame.grid(column=0, row=self.row_n, columnspan=4, rowspan=6, sticky="wens")
        self.vid_param_frame.grid_columnconfigure(0, weight=1)
        self.vid_param_row_n = self.row_n
        self.row_n = self._place_vid_param_frame(self.row_n)

        self._update_ui()

    def _place_file_input_frame(self, row_n):
        """
        Places objects in the file input frame

        Parameters
        ----------
        row_n: current row number

        Returns
        ----------
        Updated current row number
        """

        self.status_label = tk.Label(self.file_input_frame, text="-", background="yellow")
        self.status_label.grid(column=0, row=row_n, sticky="wens", columnspan=4)
        row_n += 1

        # button for loading config files
        self.load_config_file = tk.Button(self.file_input_frame, text="Load config file", highlightbackground=self.button_bg, command=self._choose_config)
        self.load_config_file.grid(column=0, row=row_n, sticky="wens", columnspan=2)

        # button for saving config files
        self.save_config_file = tk.Button(self.file_input_frame, text="Save config file", highlightbackground=self.button_bg, command=self._save_config_file)
        self.save_config_file.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        # button for selecting GPX files
        self.gpx_file_button = tk.Button(self.file_input_frame, text="Select GPX files", highlightbackground=self.button_bg, command=self._choose_gpx)
        self.gpx_file_button.grid(column=self.fi_start[0], row=self.fi_start[1]+row_n, sticky="wens", columnspan=4)
        row_n += 1

        # displays selected GPX files
        self.gpx_label = tk.Label(self.file_input_frame, text="Selected GPX files:", font=("Arial", 14, "bold"))
        self.gpx_label.grid(column=self.fi_start[0], row=self.fi_start[1]+row_n, sticky="wens", columnspan=4)
        row_n += 1
        self.selected_gpx_label = tk.Label(self.file_input_frame, text="\n".join(self.selected_gpx))
        self.selected_gpx_label.grid(column=self.fi_start[0], row=self.fi_start[1]+row_n, sticky="wens", columnspan=4)
        row_n += 1

        # selecting a background image
        self.bg_image_button = tk.Button(self.file_input_frame, text="Background Image", highlightbackground=self.button_bg, command=self._choose_bg_img)
        self.bg_image_button.grid(column=self.fi_start[0], row=self.fi_start[1]+row_n, sticky="wens", columnspan=2)

        # selecting a foreground image
        self.fg_image_button = tk.Button(self.file_input_frame, text="Foreground Image", highlightbackground=self.button_bg, command=self._choose_fg_img)
        self.fg_image_button.grid(column=self.fi_start[0]+2, row=self.fi_start[1]+row_n, sticky="wens", columnspan=2)
        row_n += 1

        # labels for selected background and foreground images
        self.bg_image_label = tk.Label(self.file_input_frame, text="")
        self.bg_image_label.grid(column=0, row=row_n, sticky="wens", columnspan=2)
        self.fg_image_label = tk.Label(self.file_input_frame, text="")
        self.fg_image_label.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        # setting top left coordinates (latitude, longitude)
        self.top_left_label = tk.Label(self.file_input_frame, text="Top left coords (lat, lon):", font=("Arial", 12, "bold"))
        self.top_left_label.grid(column=0, row=row_n, sticky="w", columnspan=2)
        self.top_left_entry = tk.Entry(self.file_input_frame)
        auto_update_entry(self.top_left_entry, ",".join([str(i) for i in self.top_left]))
        self.top_left_entry.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        # setting bottom right coordinates (latitude, longitude)
        self.bot_right_label = tk.Label(self.file_input_frame, text="Bot. right coords (lat, lon):", font=("Arial", 12, "bold"))
        self.bot_right_label.grid(column=0, row=row_n, sticky="w", columnspan=2)
        self.bot_right_entry = tk.Entry(self.file_input_frame)
        auto_update_entry(self.bot_right_entry, ",".join([str(i) for i in self.bot_right]))
        self.bot_right_entry.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        # selecting an animation type
        self.anim_type_label = tk.Label(self.file_input_frame, text="Animation Type:", font=("Arial", 12, "bold"))
        self.anim_type_label.grid(column=self.fi_start[0], row=self.fi_start[1]+row_n, sticky="w", columnspan=2)
        self.anim_type_str = tk.StringVar(self.file_input_frame)
        self.anim_type_str.set("Snake Discover")
        self.anim_type_dd = tk.OptionMenu(self.file_input_frame, self.anim_type_str, *["Snake Discover", "Simple Add"])
        self.anim_type_dd.grid(column=self.fi_start[0]+2, row=self.fi_start[1]+row_n, sticky="wens", columnspan=2)
        row_n += 1

        # setting zoom buffer
        self.zoom_buff_label = tk.Label(self.file_input_frame, text="Zoom buffer:", font=("Arial", 12, "bold"))
        self.zoom_buff_label.grid(column=0, row=row_n, sticky="w", columnspan=2)
        self.zoom_buff_entry = tk.Entry(self.file_input_frame)
        auto_update_entry(self.zoom_buff_entry, self.zoom_buff)
        self.zoom_buff_entry.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        # setting discovery radius
        self.disc_radius_label = tk.Label(self.file_input_frame, text="Discovery radius", font=("Arial", 12, "bold"))
        self.disc_radius_label.grid(column=0, row=row_n, sticky="w", columnspan=2)
        self.disc_radius_entry = tk.Entry(self.file_input_frame)
        auto_update_entry(self.disc_radius_entry, self.disc_radius)
        self.disc_radius_entry.grid(column=2, row=row_n, sticky="wens", columnspan=2)
        row_n += 1

        return row_n

    def _place_anim_param_frame(self, row_n):
        """
        Places objects in the animation parameter frame

        Parameters
        ----------
        row_n: current row number

        Returns
        ----------
        Updated current row number
        """

        # selecting marker color
        self.mark_col_label = tk.Label(self.anim_param_frame, text="Marker color:", font=("Arial", 12, "bold"))
        self.mark_col_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.mark_col_str = tk.StringVar(self.anim_param_frame)
        self.mark_col_str.set("blue")
        self.mark_col_dd = tk.OptionMenu(self.anim_param_frame, self.mark_col_str, *list(COLORS.keys()))
        self.mark_col_dd.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # selecting number of points to skip per frame
        self.skip_level_label = tk.Label(self.anim_param_frame, text="Points per frame:", font=("Arial", 12, "bold"))
        self.skip_level_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.skip_level_entry = tk.Entry(self.anim_param_frame)
        auto_update_entry(self.skip_level_entry, "5")
        self.skip_level_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # selecting number of frames to dwell on final route image
        self.dwell_frame_label = tk.Label(self.anim_param_frame, text="Dwell frames:", font=("Arial", 12, "bold"))
        self.dwell_frame_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.dwell_frame_entry = tk.Entry(self.anim_param_frame)
        auto_update_entry(self.dwell_frame_entry, "50")
        self.dwell_frame_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # clear marker checkbox
        self.mark_clr_var = tk.IntVar(self.anim_param_frame, value=1)
        self.mark_clr_cb = tk.Checkbutton(self.anim_param_frame, variable=self.mark_clr_var, text="Clear marker?", font=("Arial", 12, "bold"))
        self.mark_clr_cb.grid(column=0, row=row_n, columnspan=2, sticky="wens")

        # track elevation checkbox
        self.track_elev_var = tk.IntVar(self.anim_param_frame, value=0)
        self.track_elev_cb = tk.Checkbutton(self.anim_param_frame, variable=self.track_elev_var, text="Track elevation?", command=self._update_ui, font=("Arial", 12, "bold"))
        self.track_elev_cb.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # track distance checkbox
        self.track_dist_var = tk.IntVar(self.anim_param_frame, value=0)
        self.track_dist_cb = tk.Checkbutton(self.anim_param_frame, variable=self.track_dist_var, text="Track distance?", command=self._update_ui, font=("Arial", 12, "bold"))
        self.track_dist_cb.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 2

        return row_n

    def _place_elev_param_frame(self, row_n):
        """
        Places objects in the elevation parameter frame

        Parameters
        ----------
        row_n: current row number

        Returns
        ----------
        Updated current row number
        """

        # elevation tracking section label
        self.elev_track_sec_label = tk.Label(self.elev_param_frame, text="Elevation Tracking Parameters", font=("Arial", 14, "bold"))
        self.elev_track_sec_label.grid(column=0, row=row_n, columnspan=4, sticky="wens")
        row_n += 1

        # choosing Y span of elevation tracking animation
        self.elev_y_span_label = tk.Label(self.elev_param_frame, text="Y span:", font=("Arial", 12, "bold"))
        self.elev_y_span_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_y_span_entry = tk.Entry(self.elev_param_frame)
        auto_update_entry(self.elev_y_span_entry, "50")
        self.elev_y_span_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing X buffer of elevation tracking animation
        self.elev_x_buff_label = tk.Label(self.elev_param_frame, text="X buffer:", font=("Arial", 12, "bold"))
        self.elev_x_buff_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_x_buff_entry = tk.Entry(self.elev_param_frame)
        auto_update_entry(self.elev_x_buff_entry, "0.05")
        self.elev_x_buff_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing Y buffer of elevation tracking animation
        self.elev_y_buff_label = tk.Label(self.elev_param_frame, text="Y buffer:", font=("Arial", 12, "bold"))
        self.elev_y_buff_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_y_buff_entry = tk.Entry(self.elev_param_frame)
        auto_update_entry(self.elev_y_buff_entry, "0.90")
        self.elev_y_buff_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing the elevation tracker marker radius
        self.elev_track_rad_label = tk.Label(self.elev_param_frame, text="Elev. tracker radius:", font=("Arial", 12, "bold"))
        self.elev_track_rad_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_track_rad_str = tk.StringVar(self.elev_param_frame)
        self.elev_track_rad_str.set("1")
        self.elev_track_rad_dd = tk.OptionMenu(self.elev_param_frame, self.elev_track_rad_str, *list(range(1,6)))
        self.elev_track_rad_dd.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing the elevation tracker marker color
        self.elev_mark_col_label = tk.Label(self.elev_param_frame, text="Elev. marker col.:", font=("Arial", 12, "bold"))
        self.elev_mark_col_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_mark_col_str = tk.StringVar(self.elev_param_frame)
        self.elev_mark_col_str.set("green")
        self.elev_mark_col_dd = tk.OptionMenu(self.elev_param_frame, self.elev_mark_col_str, *list(COLORS.keys()))
        self.elev_mark_col_dd.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing the elevation tracker marker background color
        self.elev_bg_col_label = tk.Label(self.elev_param_frame, text="Background color:", font=("Arial", 12, "bold"))
        self.elev_bg_col_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.elev_bg_col_str = tk.StringVar(self.elev_param_frame)
        self.elev_bg_col_str.set("black")
        self.elev_bg_col_dd = tk.OptionMenu(self.elev_param_frame, self.elev_bg_col_str, *list(COLORS.keys()))
        self.elev_bg_col_dd.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing whether to display text readout
        self.elev_readout_var = tk.IntVar(self.elev_param_frame, value=1)
        self.elev_readout_cb = tk.Checkbutton(self.elev_param_frame, variable=self.elev_readout_var, text="Display readout?", font=("Arial", 12, "bold"))
        self.elev_readout_cb.grid(column=0, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        return row_n

    def _place_dist_param_frame(self, row_n):
        """
        Places objects in the distance parameter frame

        Parameters
        ----------
        row_n: current row number

        Returns
        ----------
        Updated current row number
        """
        # distance tracking section label
        self.dist_track_sec_label = tk.Label(self.dist_param_frame, text="Distance Tracking Parameters", font=("Arial", 14, "bold"))
        self.dist_track_sec_label.grid(column=0, row=row_n, columnspan=4, sticky="wens")
        row_n += 1

        # choosingg X buffer of distance tracking readout
        self.dist_x_buff_label = tk.Label(self.dist_param_frame, text="X buffer", font=("Arial", 12, "bold"))
        self.dist_x_buff_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.dist_x_buff_entry = tk.Entry(self.dist_param_frame)
        auto_update_entry(self.dist_x_buff_entry, "0.05")
        self.dist_x_buff_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # choosing Y buffer of distance tracking readout
        self.dist_y_buff_label = tk.Label(self.dist_param_frame, text="Y buffer", font=("Arial", 12, "bold"))
        self.dist_y_buff_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.dist_y_buff_entry = tk.Entry(self.dist_param_frame)
        auto_update_entry(self.dist_y_buff_entry, "0.10")
        self.dist_y_buff_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        return row_n

    def _place_vid_param_frame(self, row_n):
        """
        Places objects in the video parameter frame

        Parameters
        ----------
        row_n: current row number

        Returns
        ----------
        Updated current row number
        """
        
        # video saving section label
        self.vid_save_sec_label = tk.Label(self.vid_param_frame, text="Video Save Parameters", font=("Arial", 14, "bold"))
        self.vid_save_sec_label.grid(column=0, row=row_n, columnspan=4, sticky="wens")
        row_n += 1

        # button for selecting images to display
        self.disp_pic_button = tk.Button(self.vid_param_frame, text="Pictures to Display", highlightbackground=self.button_bg, command=self._choose_display_pics)
        self.disp_pic_button.grid(column=0, row=row_n, columnspan=2, sticky="wens")
        self.disp_pic_label = tk.Label(self.vid_param_frame, text="0 pics selected")
        self.disp_pic_label.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # frame rate of final video
        self.frame_rate_label = tk.Label(self.vid_param_frame, text="Frame rate (fps):", font=("Arial", 12, "bold"))
        self.frame_rate_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.frame_rate_entry = tk.Entry(self.vid_param_frame)
        auto_update_entry(self.frame_rate_entry, "30")
        self.frame_rate_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # final height of video (width calculated from aspect ratio)
        self.final_height_label = tk.Label(self.vid_param_frame, text="Final height (pix):", font=("Arial", 12, "bold"))
        self.final_height_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.final_height_entry = tk.Entry(self.vid_param_frame)
        auto_update_entry(self.final_height_entry, "500")
        self.final_height_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # file path to save video to
        self.save_folder_path_label = tk.Label(self.vid_param_frame, text="Save folder path:", font=("Arial", 12, "bold"))
        self.save_folder_path_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.save_folder_path_entry = tk.Entry(self.vid_param_frame)
        auto_update_entry(self.save_folder_path_entry, os.getcwd())
        self.save_folder_path_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # ffmpeg command
        self.ffmpeg_label = tk.Label(self.vid_param_frame, text="FFMPEG command:", font=("Arial", 12, "bold"))
        self.ffmpeg_label.grid(column=0, row=row_n, columnspan=2, sticky="w")
        self.ffmpeg_entry = tk.Entry(self.vid_param_frame)
        auto_update_entry(self.ffmpeg_entry, self.ffmpeg_command)
        self.ffmpeg_entry.grid(column=2, row=row_n, columnspan=2, sticky="wens")
        row_n += 1

        # submit button
        self.submit_button = tk.Button(self.vid_param_frame, text="Submit", highlightbackground=self.button_bg, command=self._handle_submit)
        self.submit_button.grid(column=0, row=row_n, columnspan=4, sticky="wens")
        row_n += 1

        # progress bar
        self.prog_bar = ttk.Progressbar(self.vid_param_frame, orient="horizontal", mode="indeterminate", length=50)
        self.prog_bar.grid(column=0, row=row_n, columnspan=4, sticky="wens")
        
        row_n += 1

        return row_n

    def _choose_gpx(self):
        """
        Handles GPX file selection button press event
        """
        try:
            self.selected_gpx_fpaths = list(fd.askopenfilenames(defaultextension=".gpx", filetypes=[("GPX", ".gpx")]))
            self.selected_gpx = [os.path.basename(i) for i in self.selected_gpx_fpaths]
            self.selected_gpx_label["text"] = "\n".join(self.selected_gpx)
            if len(self.selected_gpx_fpaths) > 0:
                self.status_label["text"] = "GPX file(s) loaded"
                self.status_label["background"] = "green"
            else:
                self.status_label["text"] = "-"
                self.status_label["background"] = "yellow"
        except FileNotFoundError:
            self.status_label["text"] = "GPX file not found"
            self.status_label["background"] = "red"

    def _choose_bg_img(self):
        """
        Handles background image selection button press event
        """
        try:
            self.bg_img = fd.askopenfilename(defaultextension=".png", filetypes=[("JPG", ".jpg"), ("JPEG", ".jpeg"), ("PNG", ".png")])
            if self.bg_img:
                self.status_label["text"] = "Loading background image..."
                self.status_label["background"] = "blue"
                self.bg_img_obj = cv2.imread(self.bg_img)
                self.bg_image_label["text"] = os.path.basename(self.bg_img)
                self.status_label["text"] = "Background image loaded"
                self.status_label["background"] = "green"
        except:
            self.bg_img = None
            self.bg_img_obj = None
            self.status_label["text"] = "Unable to load background image"
            self.status_label["background"] = "red"

    def _choose_fg_img(self):
        """
        Handles foreground image selection button press event
        """
        try:
            self.fg_img = fd.askopenfilename(defaultextension=".png", filetypes=[("JPG", ".jpg"), ("JPEG", ".jpeg"), ("PNG", ".png")])
            if self.fg_img:
                self.status_label["text"] = "Loading foreground image..."
                self.status_label["background"] = "blue"
                self.fg_img_obj = cv2.imread(self.fg_img)
                self.fg_image_label["text"] = os.path.basename(self.fg_img)
                self.status_label["text"] = "Foreground image loaded"
                self.status_label["background"] = "green"
        except:
            self.fg_img = None
            self.fg_img_obj = None
            self.status_label["text"] = "Unable to load foreground image"
            self.status_label["background"] = "red"

    def _update_ui(self):
        """
        Handles changes to distance and elevation tracker checkboxes
        """
        # if elevation and distance tracking boxes are both clicked...
        if self.track_elev_var.get() and self.track_dist_var.get():
            self.elev_param_frame.grid_forget()
            self.dist_param_frame.grid_forget()
            self.vid_param_frame.grid_forget()
            self.elev_param_frame.grid(column=0, row=self.elev_track_row_n, columnspan=4, rowspan=8, sticky="wens")
            self.dist_param_frame.grid(column=0, row=self.dist_track_row_n, columnspan=4, rowspan=3, sticky="wens")
            self.vid_param_frame.grid(column=0, row=self.vid_param_row_n, columnspan=4, rowspan=3, sticky="wens")

        # if only elevation tracker is clicked...
        elif self.track_elev_var.get() and (not self.track_dist_var.get()):
            self.elev_param_frame.grid_forget()
            self.dist_param_frame.grid_forget()
            self.vid_param_frame.grid_forget()
            self.elev_param_frame.grid(column=0, row=self.elev_track_row_n, columnspan=4, rowspan=8, sticky="wens")
            self.vid_param_frame.grid(column=0, row=self.vid_param_row_n, columnspan=4, rowspan=6, sticky="wens")

        # if only distance tracker is clicked...
        elif (not self.track_elev_var.get()) and self.track_dist_var.get():
            self.elev_param_frame.grid_forget()
            self.dist_param_frame.grid_forget()
            self.vid_param_frame.grid_forget()
            self.dist_param_frame.grid(column=0, row=self.elev_track_row_n, columnspan=4, rowspan=6, sticky="wens")
            self.vid_param_frame.grid(column=0, row=self.dist_track_row_n, columnspan=4, rowspan=6, sticky="wens")

        # if neither are clicked...
        elif (not self.track_elev_var.get()) and (not self.track_dist_var.get()):
            self.elev_param_frame.grid_forget()
            self.dist_param_frame.grid_forget()
            self.vid_param_frame.grid_forget()
            self.vid_param_frame.grid(column=0, row=self.vid_param_row_n, columnspan=4, rowspan=6, sticky="wens")

    def _choose_display_pics(self):
        self.disp_pics = fd.askopenfilenames(defaultextension=".png", filetypes=[("JPG", ".jpg"), ("JPEG", ".jpeg"), ("PNG", ".png")])
        if self.disp_pics:
            self.disp_pic_label["text"] = f"{len(self.disp_pics)} pics selected"
            self.status_label["text"] = "Display pictures selected"
            self.status_label["background"] = "green"
        else:
            self.disp_pics = []
            self.disp_pic_label["text"] = f"{len(self.disp_pics)} pics selected"

    def _save_config(self, fpath=None):
        """
        Saves current values of form to a JSON config file

        Parameters
        ----------
        fpath: save filepath of the JSON file
        """

        data = {"gpx_files": self.selected_gpx_fpaths,
                "bg_img": self.bg_img,
                "fg_img": self.fg_img,
                "top_left": self.top_left,
                "bot_right": self.bot_right,
                "anim_type": self.anim_type_str.get(),
                "zoom_buff": self.zoom_buff,
                "disc_radius": self.disc_radius,
                "mark_col": self.mark_col_str.get(),
                "ppf": self.ppf,
                "dwell_frames": self.dwell_frames,
                "track_elev_cb": self.track_elev_var.get(),
                "track_dist_cb": self.track_dist_var.get(),
                "elev_y_span": self.elev_y_span,
                "elev_x_buff": self.elev_x_buff,
                "elev_y_buff": self.elev_y_buff,
                "elev_track_rad": self.elev_track_rad_str.get(),
                "elev_track_col": self.elev_mark_col_str.get(),
                "elev_bg_col": self.elev_bg_col_str.get(),
                "elev_disp_rout": self.elev_readout_var.get(),
                "dist_x_buff": self.dist_x_buff,
                "dist_y_buff": self.dist_y_buff,
                "disp_pics": self.disp_pics,
                "frame_rate": self.frame_rate_entry.get(),
                "final_height": self.final_height_entry.get(),
                "save_folder": self.save_folder_path_entry.get(),
                "ffmpeg_command": self.ffmpeg_command
                }

        if fpath:
            with open(fpath, "w") as f:
                json.dump(data, f, indent=4)
        else:
            return data

    def _load_config(self, fpath):
        """
        Loads input values from a JSON config file and applies them to the GUI

        Parameters
        ----------
        fpath: path to JSON config file to be loaded
        """
        
        with open(fpath, "r") as f:
            data = json.load(f)

        # setting GPX files
        self.selected_gpx_fpaths = data["gpx_files"]
        self.selected_gpx = [os.path.basename(i) for i in self.selected_gpx_fpaths]
        self.selected_gpx_label["text"] = "\n".join(self.selected_gpx)

        # setting background image
        self.bg_img = data["bg_img"]
        if self.bg_img:
            self.bg_img_obj = cv2.imread(self.bg_img)
            self.bg_image_label["text"] = os.path.basename(self.bg_img)
        else:
            self.bg_img_obj = None
            self.bg_image_label["text"] = ""

        # setting foreground image
        self.fg_img = data["fg_img"]
        if self.fg_img:
            self.fg_img_obj = cv2.imread(self.fg_img)
            self.fg_image_label["text"] = os.path.basename(self.fg_img)
        else:
            self.fg_img_obj = None
            self.fg_image_label["text"] = ""

        # setting top left coordinates
        self.top_left = data["top_left"]
        auto_update_entry(self.top_left_entry, ",".join([str(i) for i in self.top_left]))

        # setting bottom right coordinates
        self.bot_right = data["bot_right"]
        auto_update_entry(self.bot_right_entry, ",".join([str(i) for i in self.bot_right]))
        
        # setting zoom buffer
        self.zoom_buff = data["zoom_buff"]
        auto_update_entry(self.zoom_buff_entry, self.zoom_buff)

        # setting discovery radius
        self.disc_radius = data["disc_radius"]
        auto_update_entry(self.disc_radius_entry, self.disc_radius)

        # setting animation type
        self.anim_type_str.set(data["anim_type"])

        # setting marker color
        self.mark_col_str.set(data["mark_col"])

        # setting points per frame (skip level)
        self.ppf = data["ppf"]
        auto_update_entry(self.skip_level_entry, self.ppf)

        # setting dwell frames
        self.dwell_frames = data["dwell_frames"]
        auto_update_entry(self.dwell_frame_entry, self.dwell_frames)

        # setting track elevation checkbox
        self.track_elev_var.set(data["track_elev_cb"])

        # setting track distance checkbox
        self.track_dist_var.set(data["track_dist_cb"])

        # setting elevation Y span
        self.elev_y_span = data["elev_y_span"]
        auto_update_entry(self.elev_y_span_entry, self.elev_y_span)

        # setting elevation X buffer
        self.elev_x_buff= data["elev_x_buff"]
        auto_update_entry(self.elev_x_buff_entry, self.elev_x_buff)

        # setting elevation Y buffer
        self.elev_y_buff= data["elev_y_buff"]
        auto_update_entry(self.elev_y_buff_entry, self.elev_y_buff)

        # setting elevation tracker radius
        self.elev_track_rad_str.set(data["elev_track_rad"])

        # setting elevation tracker color
        self.elev_mark_col_str.set(data["elev_track_col"])

        # setting elevation background color
        self.elev_bg_col_str.set(data["elev_bg_col"])

        # setting elevation readout checkbox
        self.elev_readout_var.set(data["elev_disp_rout"])

        # setting distance X buffer
        self.dist_x_buff = data["dist_x_buff"]
        auto_update_entry(self.dist_x_buff_entry, self.dist_x_buff)

        # setting distance Y buffer
        self.dist_y_buff = data["dist_y_buff"]
        auto_update_entry(self.dist_y_buff_entry, self.dist_y_buff)

        # setting pictures to display
        self.disp_pics = data["disp_pics"]
        self.disp_pic_label["text"] = f"{len(self.disp_pics)} pics selected"

        # setting frame rate
        self.frame_rate = data["frame_rate"]
        auto_update_entry(self.frame_rate_entry, self.frame_rate)

        # setting final height
        self.final_height = data["final_height"]
        auto_update_entry(self.final_height_entry, self.final_height)

        # setting save folder path
        self.save_folder_path = data["save_folder"]
        auto_update_entry(self.save_folder_path_entry, self.save_folder_path)

        # setting ffmpeg command
        self.ffmpeg_command = data["ffmpeg_command"]
        auto_update_entry(self.ffmpeg_entry, self.ffmpeg_command)

        self._update_ui()

        self.status_label["text"] = f"Loaded config file '{os.path.basename(fpath)}'"
        self.status_label["background"] = "green"

    def _choose_config(self):
        """
        Handles load config button event
        """
        filepath = fd.askopenfilename(defaultextension=".json", filetypes=[("JSON", ".json")])
        if filepath:
            self._load_config(filepath)

    def _save_config_file(self):
        """
        Handles save config button event
        """
        with fd.asksaveasfile(mode="w", defaultextension=".json") as f:
            if f:
                data = self._save_config()
                json.dump(data, f, indent=4)
                self.status_label["text"] = f"Saved config file {os.path.basename(f.name)}"
                self.status_label["background"] = "green"
            else:
                return


    # adapted from: https://stackoverflow.com/questions/71648197
    def _handle_submit(self):
        """
        Handles submit button event and calls asynchronous function
        """
        threading.Thread(target=lambda loop: loop.run_until_complete(self._submit()),
                args=(asyncio.new_event_loop(),)).start()
        self.submit_button["relief"] = "sunken"
        self.submit_button["state"] = "disabled"

        self.status_label["text"] = "Creating animation..."
        self.status_label["background"] = "cyan"


    async def _submit(self):
        """
        Handles submit button event
        """

        # making sure some GPX files were selected
        if not self.selected_gpx_fpaths:
            self.status_label["text"] = "Please select at least one GPX file"
            self.status_label["background"] = "red"
            return

        # making sure background image loaded properly
        if not self.bg_img:
            self.status_label["text"] = "Please select a background image"
            self.status_label["background"] = "red"
            return

        # making sure foreground image loaded properly
        if not self.fg_img:
            self.status_label["text"] = "Please select a foreground image"
            self.status_label["background"] = "red"
            return

        # making sure top left coordinates were entered correctly
        if not self.top_left_entry.get():
            self.status_label["text"] = "Please input a value for top left coordinates"
            self.status_label["background"] = "red"
            return
        else:
            if "," not in self.top_left_entry.get():
                self.status_label["text"] = "Make sure that the format for top left coords is 'lat,lon'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    [float(i) for i in self.top_left_entry.get().split(",")]
                except ValueError:
                    self.status_label["text"] = "Lats and lons for top left coords should be floats"
                    self.status_label["background"] = "red"
                    return

        # making sure zoom buffer is an integer
        if not self.zoom_buff_entry.get():
            self.status_label["text"] = "Please input a value for 'Zoom buffer'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.zoom_buff = int(self.zoom_buff_entry.get())
                if self.zoom_buff < 0:
                    self.status_label["text"] = "'Zoom buffer' must be a positive integer"
                    self.status_label["background"] = "red"
                    self.zoom_buff = 500
                    return
            except ValueError:
                self.status_label["text"] = "'Zoom buffer' must be a positive integer"
                self.status_label["background"] = "red"
                return

        # making sure discover radius is an integer
        if not self.disc_radius_entry.get():
            self.status_label["text"] = "Please input a value for 'Discovery radius'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.disc_radius = int(self.disc_radius_entry.get())
                if self.disc_radius <= 0:
                    self.status_label["text"] = "'Discovery radius' must be a nonzero positive integer"
                    self.status_label["background"] = "red"
                    self.disc_radius = 30
                    return
            except ValueError:
                self.status_label["text"] = "'Discovery radius' must be a nonzero positive integer"
                self.status_label["background"] = "red"
                return
            
        # making sure points-per-frame is an integer
        if not self.skip_level_entry.get():
            self.status_label["text"] = "Please input a value for 'Points per frame'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.ppf = int(self.skip_level_entry.get())
                if self.ppf <= 0:
                    self.status_label["text"] = "'Points per frame' must be a positive integer"
                    self.status_label["background"] = "red"
                    self.ppf = 5
                    return
            except ValueError:
                self.status_label["text"] = f"'Points per frame' should be an integer, not {type(self.skip_level_entry.get())}"
                self.status_label["background"] = "red"
                return

        # making sure dwell frames is an integer
        if not self.dwell_frame_entry.get():
            self.status_label["text"] = "Please input a value for 'Dwell frames'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.dwell_frames = int(self.dwell_frame_entry.get())
                if self.dwell_frames < 0:
                    self.status_label["text"] = "'Dwell frames' must be a positive integer"
                    self.status_label["background"] = "red"
                    self.dwell_frames = 50
                    return
            except ValueError:
                self.status_label["text"] = f"'Dwell frames' should be an integer, not {type(self.dwell_frame_entry.get())}"
                self.status_label["background"] = "red"
                return

        # checking types for elevation tracking
        if self.track_elev_var.get():
            # elevation Y span
            if not self.elev_y_span_entry.get():
                self.status_label["text"] = "Please input a value for 'Y span'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    self.elev_y_span = int(self.elev_y_span_entry.get())
                    if self.elev_y_span <= 0:
                        self.status_label["text"] = "'Y span' must be a positive integer"
                        self.status_label["background"] = "red"
                        self.elev_y_span = 50
                        return
                except ValueError:
                    self.status_label["text"] = f"'Y span' should be an integer, not {type(self.elev_y_span_entry.get())}"
                    self.status_label["background"] = "red"
                    return

            # elevation X buffer
            if not self.elev_x_buff_entry.get():
                self.status_label["text"] = "Please input a value for 'X buffer'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    self.elev_x_buff = float(self.elev_x_buff_entry.get())
                    if (self.elev_x_buff < 0.0) or (self.elev_x_buff > 1.0):
                        self.status_label["text"] = "'X buffer' must be a decimal between 0.0 and 1.0"
                        self.status_label["background"] = "red"
                        return
                except ValueError:
                    self.status_label["text"] = f"'X buffer' must be a float, not {type(self.elev_x_buff_entry.get())}"
                    self.status_label["background"] = "red"
                    return

            # elevation Y buffer
            if not self.elev_y_buff_entry.get():
                self.status_label["text"] = "Please input a value for 'Y buffer'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    self.elev_y_buff = float(self.elev_y_buff_entry.get())
                    if (self.elev_y_buff < 0.0) or (self.elev_y_buff > 1.0):
                        self.status_label["text"] = "'Y buffer' must be a decimal between 0.0 and 1.0"
                        self.status_label["background"] = "red"
                        return
                except ValueError:
                    self.status_label["text"] = f"'Y buffer' must be a float, not {type(self.elev_y_buff_entry.get())}"
                    self.status_label["background"] = "red"
                    return

        # checking types for distance tracking
        if self.track_dist_var.get():
            # distance X buffer
            if not self.dist_x_buff_entry.get():
                self.status_label["text"] = "Please input a value for 'X buffer'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    self.dist_x_buff = float(self.dist_x_buff_entry.get())
                    if (self.dist_x_buff < 0.0) or (self.dist_x_buff > 1.0):
                        self.status_label["text"] = "'X buffer' must be a decimal between 0.0 and 1.0"
                        self.status_label["background"] = "red"
                        return
                except ValueError:
                    self.status_label["text"] = f"'X buffer' must be a float, not {type(self.dist_x_buff_entry.get())}"
                    self.status_label["background"] = "red"
                    return

            # distance Y buffer
            if not self.dist_y_buff_entry.get():
                self.status_label["text"] = "Please input a value for 'Y buffer'"
                self.status_label["background"] = "red"
                return
            else:
                try:
                    self.dist_y_buff = float(self.dist_y_buff_entry.get())
                    if (self.dist_y_buff < 0.0) or (self.dist_y_buff > 1.0):
                        self.status_label["text"] = "'Y buffer' must be a decimal between 0.0 and 1.0"
                        self.status_label["background"] = "red"
                        return
                except ValueError:
                    self.status_label["text"] = f"'Y buffer' must be a float, not {type(self.dist_y_buff_entry.get())}"
                    self.status_label["background"] = "red"
                    return

        # making sure final height is an integer
        if not self.final_height_entry.get():
            self.status_label["text"] = "Please input a value for 'Final height'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.final_height = int(self.final_height_entry.get())
                if self.final_height <= 0:
                    self.status_label["text"] = "'Final height' must be a positive integer"
                    self.status_label["background"] = "red"
                    self.final_height = 500
                    return
            except ValueError:
                self.status_label["text"] = f"'Final height' should be an integer, not {type(self.final_height_entry.get())}"
                self.status_label["background"] = "red"
                return

        # making sure frame rate is an integer
        if not self.frame_rate_entry.get():
            self.status_label["text"] = "Please input a value for 'Frame rate'"
            self.status_label["background"] = "red"
            return
        else:
            try:
                self.frame_rate = int(self.frame_rate_entry.get())
                if self.frame_rate <= 0:
                    self.status_label["text"] = "'Frame rate' must be a positive integer"
                    self.status_label["background"] = "red"
                    self.final_height = 30
                    return
            except ValueError:
                self.status_label["text"] = f"'Frame rate' should be an integer, not {type(self.frame_rate_entry.get())}"
                self.status_label["background"] = "red"
                return

        self._save_config("./config_files/last.json")
        self.prog_bar.start()

        # creating the video...

        # creating the WalkMap object from the foreground image
        WMAP = WalkMap(self.fg_img_obj, self.top_left, self.bot_right)

        # load GPX files and convert them to indices
        latlon_indices = [convert_latlon_to_index(gpx_to_dataframe(i), self.top_left, self.bot_right, WMAP.shape) for i in self.selected_gpx_fpaths]

        # extract EXIF data from pictures
        pics = [Picture(i) for i in self.disp_pics]

        # create Route objects out of the latlon dataframes
        routes = [Route(i, self.zoom_buff, self.disc_radius) for i in latlon_indices]

        # adding pictures to routes
        for i in pics:
            for j in routes:
                if within_x_hours(i.date, j.date, hrs=3):
                    j.pics.append(i)

        for r in routes:
            if r.pics:
                r.address_pics()

        if self.track_dist_var.get():
            dist_params = {"unit": "mi",
                    "x_buff": self.dist_x_buff,
                    "y_buff": self.dist_y_buff
                    }
        else:
            dist_params = None

        if self.track_elev_var.get():
            elev_params = {"type": "prof",
                    "kws": {"y_span": self.elev_y_span,
                        "x_buff": self.elev_x_buff,
                        "y_buff": self.elev_y_buff,
                        "rad": int(self.elev_track_rad_str.get()),
                        "color": COLORS[self.elev_mark_col_str.get()],
                        "bg": COLORS[self.elev_bg_col_str.get()],
                        "text": int(self.elev_readout_var.get())
                        }
                    }
        else:
            elev_params = None

        tstamp = timestamp()

        # creating the Snake Discover video
        if self.anim_type_str.get() == "Snake Discover":
            save_path = os.path.join(self.save_folder_path_entry.get(), f"{tstamp}_snakediscover.mp4")
            WMAP.snake_path_discover(routes=routes, 
                discover_map=self.bg_img_obj, 
                save_path=save_path,
                marker_col=COLORS[self.mark_col_str.get()],
                skip_level=self.ppf,
                final_height=self.final_height,
                dwell_f=self.dwell_frames,
                fps=self.frame_rate,
                clear_marker=self.mark_clr_var.get(),
                distance=dist_params,
                elev=elev_params)

            if self.ffmpeg_entry.get():
                final_ffmpeg_command = self.ffmpeg_command
                for k,v in {"<file>": save_path, "<out_file>": os.path.join(self.save_folder_path_entry.get(), f"{tstamp}_snakediscover_compressed.mp4")}.items():
                    final_ffmpeg_command = final_ffmpeg_command.replace(k, v)
                os.system(final_ffmpeg_command)

            self.status_label["text"] = f"Saved animation '{os.path.basename(save_path)}'"
            self.status_label["background"] = "green"

        # adding routes to the map without animation
        elif self.anim_type_str.get() == "Simple Add":
            for r in routes:
                WMAP.draw_route_discover(r, self.bg_img_obj)

            self.status_label["text"] = f"Saved map '{os.path.basename(save_path)}'"
            self.status_label["background"] = "green"

        save_path = os.path.join(self.save_folder_path_entry.get(), f"{tstamp}_map.png")
        cv2.imwrite(save_path, WMAP.image)

        self.prog_bar.stop()

        self.submit_button["relief"] = "raised"
        self.submit_button["state"] = "normal"

        

