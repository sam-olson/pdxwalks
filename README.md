# pdxwalks

A Python program for tracking how much of a map you've explored based on GPS data. I use this software for mapping my walks around Portland, OR, although it should be straightforward to make it work for other cities as well.

The software works by plotting data from GPX files. GPX is a common output file format for GPS devices. I tend to use the Asics Runkeeper app, since it allows you to export your data from the Asics website.

## Features
- Video game-like "discovery" animations for plotting walking/running/biking routes
- Pixel-by-pixel rendering of each animation frame
- Includes metrics for tracking elevation and distance traveled over time
- Display pictures from your walk/run/bike ride, with their location on the map automatically determined through photo metadata
- Ability to customize layout of features in output video
- GUI for ease of use

## Getting started
`pdxwalks` requires that [Python3](https://www.python.org/) is installed on your machine. The software also requires some third-party packages that must be installed prior to usage. The packages are listed in the `requirements.txt` file. To install these packages, navigate to the directory where you downloaded this repository and run the following command (on a Unix-based system):
```bash
python3 -m pip install -r requirements.txt
```

Or on a Windows system:
```bash
py -m pip install -r requirements.txt
```

## Downloading the example maps
The full size map of Portland used in the example program is just under 100 MB, which is an impractical size to host on Github. However it is [available on Dropbox](https://www.dropbox.com/sh/iz3gre60gbrs1xc/AAAei03sb0_nQAm3_5ImBwYya?dl=0), in addition to a map of Portland containing only streets and neighborhood boundaries, which will serve as the top layer of the resulting video output. Download these two images and place them in the `source_maps` directory.

## Running the example program
`pdxwalks` comes with an example program (`example.py`) that demonstrates how to use some of the functions included in the package. To run this example, navigate to the directory where you donwloaded this repository and run the following command (on a Unix-based system):
```bash
python3 example.py
```

Or on a windows system:
```bash
py example.py
```

This program will plot one of the example routes and save the animation to the current directory.

## GUI Tutorial

The GUI makes it straightforward to enter parameters that customize the final animation to your liking. It also provides convenient ways to assign pathing for saving/loading files.

![gui](https://github.com/sam-olson/pdxwalks/blob/master/assets/gui_layout.png)

The green area at the top of the GUI in the above image is a status bar that provides feedback to the user. When the value of an input is of the incorrect type or out of the range of acceptable values, the status bar will turn red and provide detail of what the user must fix to successfully create an animation.

![value_error](https://github.com/sam-olson/pdxwalks/blob/master/assets/value_error.png)

Configuration files can be saved and loaded in JSON format so that the user does not have to constantly make changes to the input parameters every time they want to create an animation video in the same style. The most recent successfully submitted parameters are stored in `config_files/last.json`. This configuration file is automatically loaded every time the program begins. The default parameters can also be restored by loading `config_files/default.json`. The user can save the current parameters to a configuration file at any point by using the "Save config file" button.

To use the GUI, navigate to the main `pdxwalks` folder as downloaded/cloned from Github and run the following command (on a Unix-based system):
```bash
python3 app.py
```

If on a Windows based system:
```bash
py app.py
```

Below is an example frame of a "Snake Discover" animation, detailing the various parameters that can be adjusted:
![snake](https://github.com/sam-olson/pdxwalks/blob/master/assets/snakediscover_output.png)

### Parameters
##### Load config file
A button that opens a file dialog and asks the user to select a .json configuration file. The inputs are automatically updated to reflect the contents of the file

##### Save config file
A button that opens a file dialog and asks the user to select a path to save the current parameters to in a .json config file

##### Select GPX files
A button that opens a file dialog and asks the user to select one or more GPX files. These files contain GPS data (time, latitude, longitude, elevation) and are used to plot the routes in the animation. Once selected, the names of the GPX files will appear in the region below this button.

##### Background Image
A button that opens a file dialog and asks the user to select an image (.jpg or .png) that represents the image being "discovered" by your walk/run/bike ride. In most cases, this will be an image of a map. Included in this repository is a high-resolution map of Portland (`source_maps/full_image.png`) that can be used as an example. This map consists of many smaller map tiles stitched together, resulting in a final file size of just under 100 MB. The map tiles were downloaded from [Open Street Map](https://www.openstreetmap.org/#map=5/38.007/-95.844). The selected file name is displayed below the button.

##### Foreground Image
A button that opens a file dialog and asks the user to select an image (.jpg or .png) that represents the currently exposed regions of the map. Typically this image will contain the results of previous animations (i.e., you start with the output saved from a previous run). At the beginning, this will typically be an image of black pixels in the same shape as the Background Image described above. An example of a starting image for Portland is located at `source_maps/portland_nbhd_sourcemap.png`. This image consists of outlines of all neighborhoods in white, as well as all streets colored by which sextant of the city they belong to (blue = North Portland, green = Northwest Portland, red = Northeast Portland, magenta = Southwest Portland, cyan = South Portland, and yellow = Southeast Portland). The streets and neighborhood boundaries help to determine areas that you have not been to yet when planning a route. The selected file name is displayed below the button.

##### Top Left and Bot Right coord entries
It is necessary to note the latitude and longitude of the top left and bottom right corners of the map on which you are plotting routes. Each GPS data point must be assigned an x and y index based on its relation to these two points and the size of the image. To find these points, it is usually necessary to go to Google Maps and double click as close as possible to the corners of your map. This will set a pin at that location and display the latitude and longitude. These points must be entered into their respective inputs in the format 'latitude,longitude'. For the background image located at `source_maps/portland_full_image.png`, the top left and bottom right coordinates are `45.6065,-122.8138` and `45.4535,-122.5462` respectively.

##### Animation Type
This dropdown allows the user to select the type of animation to create. The default is "Snake Discover", which animates the path of your workout and displays your progress as if you are "discovering" regions on a video game map. There is currently only one other option available, "Simple Add", which adds your route to the map without creating an animation (useful for bulk-adding workouts).

##### Zoom Buffer
The zoom buffer represents the number of pixels (vertical and horizontal) that will remain as a buffer between the route animation and the edge of the frame when zooming in to track a route. The input should be a positive integer (the default is 500).

##### Discovery Radius
The discovery radius is the radius of the circle that is drawn around each point of the GPX file during the animation. The pixels within this circle will "uncloud" the map. The input should be a non-zero positive integer (the default is 30).

##### Marker Color
This input dictates the color of the marker that tracks the location of each point in the GPX file. The default value is "blue", however there are several other colors to choose from in the drop-down menu.

##### Points Per Frame
This input controls the number of points in the GPX file that are updated for each frame of the video. The lower the value, the smoother the animation will be (at the cost of render time and final file size). The value should be a non-zero positive integer (the default value is 2).

##### Dwell Frames
Controls the number of frames that the animation dwells for at the end of the route. The value should be a positive integer or zero (default is 50 frames).

##### Clear Marker checkbox
This checkbox dictates whether or not the central marker that tracks the exact position during the workout will be cleared after every new frame. If this box is checked, the marker appears as an individual dot in a new location every frame. If the box is not checked, the marker will be not be cleared each frame and will appear as a line in the final animation.

##### Track Elevation checkbox
This checkbox determines whether or not elevation tracking will be displayed on the final animation video. The elevation tracking plots the elevation of your route over the entire distance of the route (similar to how Google Maps will show the elevation loss/gain of a route). If it is selected, additional inputs will appear in the GUI (see below).

##### Track Distance checkbox
Determines whether or not distance tracking will be displayed on the final animation video. If selected, a textbox displaying the total distance traveled will appear and update with each frame, and additional inputs will appear in the GUI (see below).

##### Y span (elevation tracking parameters)
Defines the number of pixels that the elevation tracker will occupy in the Y (height) direction. The value should be a non-zero, positive integer (default is 50).

##### X buffer (elevation tracking parameters)
Describes the percent of the width of the video that should be used as buffer space for the elevation tracker. The higher the value, the less width is taken up by the tracker. The value should be a floating point number between 0.0 and 1.0 (the default is 0.05). For example, if the final video width is 600 pixels, and the X buffer is 0.05, the total buffer pixels will be 600*0.05 = 30 pixels, or 15 pixels on both sides of the elevation tracker.

##### Y buffer (elevation tracking parameters)
Describes the percent of hte height of the video that should be used as a buffer space between the top of the video and the top of the elevation tracker (essentially it determines where in the Y-dimension the tracker will be positioned). The value should be a floating point number between 0.0 and 1.0 (the default is 0.9). For example, if the final video width is 600 pixels, and the Y buffer is 0.9, the top of the elevation tracker will be 540 pixels from the top of the image. If the Y span is set to the default of 50, the bottom of the elevation tracker will then be 590 pixels from the top (and 10 pixels from the bottom).

##### Elev. tracker radius (elevation tracking parameters)
Determines the radius of the elevation tracking marker. The value should be a non-zero, positive integer (default value is 1 pixel).

##### Elev. marker col. (elevation tracking parameters)
Sets the color of the elevation tracking marker. The default value is "red", and there are additional options to choose from in the drop-down menu.

##### Background color (elevation tracking parameters)
Sets the color of the background on which the elevation tracker is drawn. The default value is "black", and there are additional options to choose from in the drop-down menu.

##### Display readout checkbox (elevation tracking parameters)
If selected, the program will add a live readout of the current elevation each in each frame

##### X buffer (distance tracking parameters)
Describes percent of width of video from the left-hand side of the frame that should be used as buffer space for the distance tracker (similar to the X buffer for the elevation tracker as described above). The value should be a floating point number between 0.0 and 1.0 (default is 0.05).

##### Y buffer (distance tracking parameters)
Describes percent of height of video from top of the frame that should be used as buffer space for the distance tracker (similar to the Y buffer for the elevation tracker as described above). The value should be a floating point number between 0.0 and 1.0 (default is 0.1).

##### Pictures to Display button (video save parameters)
This button allows the user to select one or more pictures taken on the route(s). The pictures will be automatically assigned to the proper route by comparing timestamps. They will then be included in the final animation in the location on the map at which they were taken. The number of photos currently selected will be listed in the area to the right of the button.

##### Frame rate
The frame rate of the final video in frames per second. The value should be a non-zero, positive integer (default value is 30 fps).

##### Final height
The final height of the video in pixels. The value should be a non-zero, positive integer (default value is 500 pix).

##### Save folder path
The path where the video will be saved to (default is the current directory in which the application is saved).

##### FFMPEG command
This entry is used to create an FFMPEG command that will run after the main Python code and compress the video. When the code runs, "<file>" will be replaced with the filename as saved by the Python code, and "<out_file>" will be replaced with the filename followed by "_compressed" (i.e., filename_compressed.mp4). If you do not want an FFMPEG command to run, simply delete all text from this entry.
