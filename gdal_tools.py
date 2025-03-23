#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 14:03:14 2025

@author: pelagia
"""

import numpy as np
from osgeo import gdal, osr


def raster2array(file, bands=None):
    # read raster file as numpy.array
    
    # --- Input ---
    # file:         (str)       raster file to read
    # bands:        (list)      list of selected bands (e.g. [0, 1, 3])
    #                           if none selected, all will be read
    # --- Output ---
    # array         (ndarray)   numpy.array [rows x columns x bands]
    #-----------------------
    
    # open raster with gdal
    ds = gdal.Open(file, gdal.GA_ReadOnly)
    
    # get image dimensions
    nbands = ds.RasterCount # number of bands
    cols = ds.RasterXSize # numbers of columns
    rows = ds.RasterYSize # number of rows
    
    
    if not bands:
        bands = list(range(nbands))
        
    # make the array that will store the image
    array = np.empty((rows, cols, len(bands)))
        
    # get each band and read as np array
    for n in range(len(bands)):
        array[:,:,n] = ds.GetRasterBand(bands[n]+1).ReadAsArray()
        
        nan_value = ds.GetRasterBand(bands[n]+1).GetNoDataValue()
        if nan_value:
            array[:,:,bands[n]][array[:,:,bands[n]]==nan_value] = np.nan
    
    ds = None
    
    return array




def array2raster(newRasterfn, tif_file, array, dtype):
    # save GTiff file from numpy.array
    
    # --- Input ---
    # newRasterfn:  (str)       save file name
    # tif_file:     (str)       original tif file
    # array:        (ndarray)   numpy.array
    # dtype:        (str)       Byte or Float32
    #-----------------------


    cols = array.shape[1]
    rows = array.shape[0]
    
    dataset = gdal.Open(tif_file)
    originX, pixelWidth, b, originY, d, pixelHeight = dataset.GetGeoTransform() 
    
    driver = gdal.GetDriverByName('GTiff')
    
    # set data type to save
    GDT_dtype = gdal.GDT_Unknown
    if dtype == "Byte": 
        GDT_dtype = gdal.GDT_Byte
    elif dtype == "Float32":
        GDT_dtype = gdal.GDT_Float32
    else:
        print("Not supported data type.")
    
    # set number of band
    if array.ndim == 2:
        band_num = 1
    else:
        band_num = array.shape[2]
    
    outRaster = driver.Create(newRasterfn, cols, rows, band_num, GDT_dtype)
    outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
    
    # Loop over all bands.
    for b in range(band_num):
        outband = outRaster.GetRasterBand(b + 1)
        # Read in the band's data into the third dimension of our array
        if band_num == 1:
            outband.WriteArray(array)
        else:
            outband.WriteArray(array[:,:,b])
    
    # setting srs from input tif file
    prj=dataset.GetProjection()
    outRasterSRS = osr.SpatialReference(wkt=prj)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    
    outband.FlushCache()   
    