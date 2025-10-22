#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jan 21 14:03:14 2025

@author: pelagia
"""

import numpy as np
from osgeo import gdal, osr, ogr



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




def array2raster(newRasterfn, array, dtype, ref_img=None, prj=None, geotransform=None):
    # save GTiff file from numpy.array
    
    # --- Input ---
    # newRasterfn:  (str)       save file name
    # tif_file:     (str)       original tif file
    # array:        (ndarray)   numpy.array
    # dtype:        (str)       Byte or Float32
    #-----------------------
    
    if ref_img is not None:
        dataset = gdal.Open(ref_img)
        # get geotransfoorm form reference image
        originX, pixelWidth, b, originY, d, pixelHeight = dataset.GetGeoTransform()
        # get srs from reference image
        prj=dataset.GetProjection()
        
        dataset = None
        
    else:
        if prj is not None and geotransform is not None:
            originX, pixelWidth, b, originY, d, pixelHeight = geotransform
        else:
            raise ValueError('If reference mage is not given, projection and geotransform should be provided.')
        
        
    # image columns and rows
    cols = array.shape[1]
    rows = array.shape[0]
    
    # set number of band
    if array.ndim == 2:
        nbands = 1
    else:
        nbands = array.shape[2]
        
    print(f'Image dimensions: rows: {rows}, columns: {cols}, bands: {nbands}')
    
    # set format
    driver = gdal.GetDriverByName('GTiff')
    
    # set data type to save
    GDT_dtype = gdal.GDT_Unknown
    if dtype == "Byte": 
        GDT_dtype = gdal.GDT_Byte
    elif dtype == "Float32":
        GDT_dtype = gdal.GDT_Float32
    else:
        print("Not supported data type.")
    
    outRaster = driver.Create(newRasterfn, cols, rows, nbands, GDT_dtype)
    outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
    
    # Loop over all bands.
    for b in range(nbands):
        outband = outRaster.GetRasterBand(b + 1)
        # Read in the band's data into the third dimension of our array
        if nbands == 1:
            outband.WriteArray(array)
        else:
            outband.WriteArray(array[:,:,b])
    
    # setting srs from input tif file
    outRasterSRS = osr.SpatialReference(wkt=prj)
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    
    outband.FlushCache()   
    
    print(f'Image was saved sucessfully at {newRasterfn}')  
    print('--')
    
    
    
    
def transform_coordinates(x, y, espg_in, espg_out):

    # Spatial Reference System
    inputEPSG = espg_in
    outputEPSG = espg_out

    # create a geometry from coordinates
    point = ogr.Geometry(ogr.wkbPoint)
    point.AddPoint(x, y)

    # create coordinate transformation
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(inputEPSG)

    outSpatialRef = osr.SpatialReference()
    outSpatialRef.ImportFromEPSG(outputEPSG)

    coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
    
    # transform point
    point.Transform(coordTransform)

    # print point in EPSG out
    return point.GetX(), point.GetY()