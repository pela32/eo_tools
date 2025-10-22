#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 14:38:59 2025

@author: pelagia
"""

import os
import glob
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from gdal_tools import raster2array



def subset(img, lon, lat, lon_min, lon_max, lat_min, lat_max):
    """
    Subsets a image based on geographic boundaries (lon/lat box).

    Inputs
    ----------
    img [np array] :           Path to the raster image file containing data values
    lon [np array] :           Path to the raster file containing longitude values for each pixel
    lat [np array] :           Path to the raster file containing latitude values for each pixel
    lon_min, lon_max [float] : Minimum and maximum longitude defining the region of interest
    lat_min, lat_max [float] : Minimum and maximum latitude defining the region of interest

    Outputs
    -------
    img_sub [np array] :       The subset of the input image corresponding to the specified lon/lat box.
                               Pixels outside the box are set to NaN.
    """
    
    # --- Check if lon/lat grids match image size ---
    # If not, perform interpolation to align lon/lat to image grid
    if not img.shape == lon.shape:

        # Define the coordinate system of the original lon/lat arrays
        x = np.linspace(1, lon.shape[0], lon.shape[0])
        y = np.linspace(1, lon.shape[1], lon.shape[1])
    
        # Define the coordinate system of the target image grid
        xx = np.linspace(1, img.shape[0], img.shape[0])
        yy = np.linspace(1, img.shape[1], img.shape[1])

        # Create meshgrids for interpolation (using matrix indexing)
        X, Y = np.meshgrid(xx, yy, indexing='ij')
        
        # --- Interpolate longitude values to image grid ---
        interp = RegularGridInterpolator((x, y), lon, bounds_error=False, fill_value=None)
        lon_interp = interp((X, Y))

        # --- Interpolate latitude values to image grid ---
        interp = RegularGridInterpolator((x, y), lat, bounds_error=False, fill_value=None)
        lat_interp = interp((X, Y))
    
    else:
        # If shapes already match, no interpolation needed
        lon_interp = lon
        lat_interp = lat

    # --- Subset the image ---
    # Create a mask selecting only pixels within the specified lon/lat bounds
    img_sub = np.where(
        (lon_interp > lon_min) & (lon_interp < lon_max) &
        (lat_interp > lat_min) & (lat_interp < lat_max),
        img,  # keep pixel values inside the bounds
        np.nan  # assign NaN outside the bounds
    )
    
    return img_sub

