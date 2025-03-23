#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 16 14:38:59 2025

@author: pelagia
"""

import os
import glob
import numpy as np
import scipy as sp
import osgeo.gdal as gdal

## GET ionosphere delay phase for subset of image

lon_min = 26.5
lon_max = 27.5
lat_min = 66.5
lat_max = 67.5


ion_files = sorted(glob.glob('/media/pelagia/Elements/InSAR_Iono_ISCE/stackHV/proc/dates_ion/*_8rlks_16alks.ion'))
lon_file = '/media/pelagia/Elements/InSAR_Iono_ISCE/stackHH/proc/pairs_ion/200406-200420/ion/ion_cal/lon_32rlks_64alks.lon'
lat_file = '/media/pelagia/Elements/InSAR_Iono_ISCE/stackHH/proc/pairs_ion/200406-200420/ion/ion_cal/lat_32rlks_64alks.lat'


def get_image(file):
    
    ds = gdal.Open(file)
    image = ds.GetRasterBand(2).ReadAsArray()
    ds = None
    
    return image

# read image data
ion = get_image(ion_files[0])

lon = get_image(lon_file)
lat = get_image(lat_file)


# 2-D bilinear interpolation for lon and lat to ion grid

x = np.linspace(1, lon.shape[0], lon.shape[0])
y = np.linspace(1, lon.shape[1], lon.shape[1])

xx = np.linspace(1, lon.shape[0], ion.shape[0])
yy = np.linspace(1, lon.shape[1], ion.shape[1])

X, Y = np.meshgrid(xx, yy, indexing='ij')

interp = sp.interpolate.RegularGridInterpolator((x, y), lon, bounds_error=False, fill_value=None)

lon_interp = interp((X,Y))

interp = sp.interpolate.RegularGridInterpolator((x, y), lat, bounds_error=False, fill_value=None)

lat_interp = interp((X,Y))


# crop ion images
for ion_file in ion_files:
    
    ion = get_image(ion_file)
    
    ion_crop = np.where((lon_interp>26.5) * (lon_interp<27.5) * (lat_interp>66.5) * (lat_interp<67.5), ion, np.nan)
    
    print(np.nanmean(ion_crop))

