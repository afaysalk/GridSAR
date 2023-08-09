#!/usr/bin/env python3

from argparse import ArgumentParser, RawTextHelpFormatter
import collections
import fnmatch
import folium
from folium.plugins import HeatMap
import ijson
import json
import os
from progressbar import ProgressBar, Bar, ETA, Percentage
from utils import *
import webbrowser
from xml.etree import ElementTree
from xml.dom import minidom
import zipfile
import pandas as pd
import numpy as np
import matplotlib as plt
from scipy.interpolate import griddata
import geojson
import branca



def get_geojson_grid(upper_right, lower_left, n):
    """Returns a grid of geojson rectangles, and computes the exposure 
        in each section of the grid based on the vessel data.

    Parameters
    ----------
    upper_right: array_like
        The upper right hand corner of "grid of grids" (the default is 
   the upper right hand [lat, lon] of the USA).

    lower_left: array_like
        The lower left hand corner of "grid of grids"  (the default is 
     the lower left hand [lat, lon] of the USA).

    n: integer
        The number of rows/columns in the (n,n) grid.

    Returns
    -------

    list
        List of "geojson style" dictionary objects   
    """

    all_boxes = []

    lat_steps = np.linspace(lower_left[0], upper_right[0], n+1)
    lon_steps = np.linspace(lower_left[1], upper_right[1], n+1)

    lat_stride = lat_steps[1] - lat_steps[0]
    lon_stride = lon_steps[1] - lon_steps[0]

    for lat in lat_steps[:-1]:
        for lon in lon_steps[:-1]:
            # Define dimensions of box in grid
            upper_left = [lon, lat + lat_stride]
            upper_right = [lon + lon_stride, lat + lat_stride]
            lower_right = [lon + lon_stride, lat]
            lower_left = [lon, lat]

            # Define json coordinates for polygon
            coordinates = [
                upper_left,
                upper_right,
                lower_right,
                lower_left,
                upper_left
            ]

            geo_json = {"type": "FeatureCollection",
                        "properties":{
                            "lower_left": lower_left,
                            "upper_right": upper_right
                        },
                        "features":[]}

            grid_feature = {
                "type":"Feature",
                "geometry":{
                    "type":"Polygon",
                    "coordinates": [coordinates],
                }
            }

            geo_json["features"].append(grid_feature)

            all_boxes.append(geo_json)

    return all_boxes 




# Used a def so that if you wish to add interactivity you can do that easily later on.
def gridder(min_hour,max_hour,n,m):

        # Add a column with ones, then calculate sum and generate the heat
        sliceDF = pd.read_csv("new.csv")
        sliceDF.dropna(subset=["Latitude", "Longitude"], inplace=True)
        
    
        #boundaries of the main rectangle
        upper_right = [52.665317, -1.684482]
        lower_left = [52.379884, -2.184111]
        
        # Creating a grid of nxn from the given cordinate corners     
        grid = get_geojson_grid(upper_right, lower_left , n)
        # Holds number of points that fall in each cell & time window if provided
        counts_array = []
        
        # Adding the total number of visits to each cell
        for box in grid:
            # get the corners for each cell
            print(box["properties"]["upper_right"])
            upper_right = box["properties"]["upper_right"]
            lower_left = box["properties"]["lower_left"]
            print(box["properties"]["upper_right"])
        # check to make sure it's in the box and between the time window if time window is given 
            mask = ((sliceDF.Latitude <= upper_right[1]) & (sliceDF.Latitude >= lower_left[1]) &
                (sliceDF.Longitude <= upper_right[0]) & (sliceDF.Longitude >= lower_left[0]) )
        # Number of points that fall in the cell and meet the condition 
            counts_array.append(len(sliceDF[mask]))
            
        # creating a base map 
        # Add GeoJson to map
        for i, geo_json in enumerate(grid):
                relativeCount = counts_array[i]*1000
                color = plt.cm.YlGn(relativeCount)
                color = plt.colors.to_hex(color)
                gj = folium.GeoJson(geo_json,
                        style_function=lambda feature, color=color: {
                            'fillColor': color,
                            'color':"gray",
                            'weight': 0.5,
                            'dashArray': '6,6',
                            'fillOpacity': 0.8,
                        })
                   
                m.add_child(gj)
            
        colormap = branca.colormap.linear.YlGn_09.scale(0, 1)
        colormap = colormap.to_step(index=[0, 0.3, 0.6, 0.8 , 1])
        colormap.caption = 'Relative density of fleet activity per cell'
        colormap.add_to(m)
        return m
 
class Generator:
    def __init__(self):
        self.coordinates = collections.defaultdict(int)
        self.max_coordinates = (0, 0)
        self.max_magnitude = 0
        self.resetStats()

    def resetStats(self):
        self.stats = {
            "Data points": 0
        }

    @staticmethod
    


    

    def loadKMLData(self, file_name, date_range):
        """Loads the Google location data from the given KML file.

        Arguments:
            file_name {string or file} -- The name of the KML file
                (or an open file-like object) with the Google location data.
            date_range {tuple} -- A tuple containing the min-date and max-date.
                e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
        """
        xmldoc = minidom.parse(file_name)
        gxtrack = xmldoc.getElementsByTagName("gx:coord")
        when = xmldoc.getElementsByTagName("when")
        w = [Bar(), Percentage(), " ", ETA()]

        with ProgressBar(max_value=len(gxtrack), widgets=w) as pb:
            for i, number in enumerate(gxtrack):
                loc = (number.firstChild.data).split()
                coords = (round(float(loc[1]), 6), round(float(loc[0]), 6))
                date = when[i].firstChild.data
                if dateInRange(date[:10], date_range):
                    self.updateCoord(coords)
                pb.update(i)

    def loadGPXData(self, file_name, date_range):
        """Loads location data from the given GPX file.

        Arguments:
            file_name {string or file} -- The name of the GPX file
                (or an open file-like object) with the GPX data.
            date_range {tuple} -- A tuple containing the min-date and max-date.
                e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
        """
        xmldoc = minidom.parse(file_name)
        gxtrack = xmldoc.getElementsByTagName("trkpt")
        w = [Bar(), Percentage(), " ", ETA()]

        with ProgressBar(max_value=len(gxtrack), widgets=w) as pb:
            for i, trkpt in enumerate(gxtrack):
                lat = trkpt.getAttribute("lat")
                lon = trkpt.getAttribute("lon")
                coords = (round(float(lat), 6), round(float(lon), 6))
                date = trkpt.getElementsByTagName("time")[0].firstChild.data
                if dateInRange(date[:10], date_range):
                    self.updateCoord(coords)
                pb.update(i)

    



    





    def updateCoord(self, coords):
        self.coordinates[coords] += 1
        self.stats["Data points"] += 1
        if self.coordinates[coords] > self.max_magnitude:
            self.max_coordinates = coords
            self.max_magnitude = self.coordinates[coords]

    def generateMap(self, settings):
        """Generates the heatmap.

        Arguments:
            settings {dict} -- The settings for the heatmap.

        Returns:
            Map -- The Heatmap.
        """
        tiles = settings["tiles"]
        zoom_start = settings["zoom_start"]
        radius = settings["radius"]
        blur = settings["blur"]
        min_opacity = settings["min_opacity"]
        max_zoom = settings["max_zoom"]

        map_data = [(coords[0], coords[1], magnitude)
                    for coords, magnitude in self.coordinates.items()]

       
       # Generate map
        m = folium.Map(location=self.max_coordinates,
                        zoom_start=zoom_start,
                        tiles=tiles,
                        attr="<a href=https://github.com/luka1199/geo-heatmap>geo-heatmap</a>")

            # Generate heat map
        heatmap = HeatMap(map_data,
                            max_val=self.max_magnitude,
                            min_opacity=min_opacity,
                            radius=radius,
                            blur=blur,
                            max_zoom=max_zoom)

        
        # limiting time window for our data to 8 am - 5 pm and also grid is 20 x 20 
        m=gridder(0,24,20,m)
        m.add_child(heatmap)

        
        return m


    
    

    def run(self, data_files, output_file, date_range, stream_data, settings):
        """Load the data, generate the heatmap and save it.

        Arguments:
            data_files {list} -- List of names of the data files with the Google
                location data or the Google takeout ZIP archive.
            output_file {string} -- The name of the output file.
            date_range {tuple} -- A tuple containing the min-date and max-date.
                e.g.: (None, None), (None, '2019-01-01'), ('2017-02-11'), ('2019-01-01')
            stream_data {bool} -- Stream option.
            settings {dict} -- The settings for the heatmap.
        """
        self.resetStats()

        for i, data_file in enumerate(data_files):
            print("\n({}/{}) Loading data from {}".format(
                i + 1,
                len(data_files) + 2,
                data_file))
            
            if data_file.endswith(".gpx"):
                self.loadGPXData(data_file, date_range)
            else:
                raise NotImplementedError(
                    "Unsupported file extension for {!r}".format(data_file))

        print("\n({}/{}) Generating heatmap".format(
            len(data_files) + 1,
            len(data_files) + 2))
        m = self.generateMap(settings)
        print("\n({}/{}) Saving map to {}\n".format(
            len(data_files) + 2,
            len(data_files) + 2,
            output_file))
        m.save(output_file)

        print("Stats:")
        for name, stat in self.stats.items():
            print("{}: {}".format(name, stat))
        print()

if __name__ == "__main__":
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "files", metavar="file", type=str, nargs="+", help="Any of the following files:\n"
        "- Your location history JSON file from Google Takeout\n"
        "- Your location history KML file from Google Takeout\n"
        "- The takeout-*.zip raw download from Google Takeout \nthat contains either of the above files\n"
        "- A GPX file containing GPS tracks")
    parser.add_argument("-o", "--output", dest="output", type=str, required=False,
                        help="Path of heatmap HTML output file.", default="heatmap.html")
    parser.add_argument("--min-date", dest="min_date", metavar="YYYY-MM-DD", type=str, required=False,
                        help="The earliest date from which you want to see data in the heatmap.")
    parser.add_argument("--max-date", dest="max_date", metavar="YYYY-MM-DD", type=str, required=False,
                        help="The latest date from which you want to see data in the heatmap.")
    parser.add_argument("-s", "--stream", dest="stream", action="store_true", help="Option to iteratively load data.")
    parser.add_argument("--map", "-m", dest="map", metavar="MAP", type=str, required=False, default="OpenStreetMap",
                        help="The name of the map tiles you want to use.\n" \
                        "(e.g. 'OpenStreetMap', 'StamenTerrain', 'StamenToner', 'StamenWatercolor')")
    parser.add_argument("-z", "--zoom-start", dest="zoom_start", type=int, required=False,
                        help="The initial zoom level for the map. (default: %(default)s)", default=6)
    parser.add_argument("-r", "--radius", type=int, required=False,
                        help="The radius of each location point. (default: %(default)s)", default=7)
    parser.add_argument("-b", "--blur", type=int, required=False,
                        help="The amount of blur. (default: %(default)s)", default=4)
    parser.add_argument("-mo", "--min-opacity", dest="min_opacity", type=float, required=False,
                        help="The minimum opacity of the heatmap. (default: %(default)s)", default=0.2)
    parser.add_argument("-mz", "--max-zoom", dest="max_zoom", type=int, required=False,
                        help="The maximum zoom of the heatmap. (default: %(default)s)", default=4)


    args = parser.parse_args()
    data_file = args.files
    output_file = args.output
    date_range = args.min_date, args.max_date
    stream_data = args.stream
    settings = {
        "tiles": args.map,
        "zoom_start": args.zoom_start,
        "radius": args.radius,
        "blur": args.blur,
        "min_opacity": args.min_opacity,
        "max_zoom": args.max_zoom
    }

    generator = Generator()
    generator.run(data_file, output_file, date_range, stream_data, settings)
    # Check if browser is text-based
    if not isTextBasedBrowser(webbrowser.get()):
        try:
            print("[info] Opening {} in browser".format(output_file))
            webbrowser.open("file://" + os.path.realpath(output_file))
        except webbrowser.Error:
            print("[info] No runnable browser found. Open {} manually.".format(
                output_file))
            print("[info] Path to heatmap file: \"{}\"".format(os.path.abspath(output_file)))
