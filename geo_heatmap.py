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
