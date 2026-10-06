#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  8 13:58:45 2023
Updated on Tue Oct 10 18:46:00 2026

@author: pelagia


Copernicus Data Space Ecosystem OData Search and Download Script
-----------


Description
-----------
This script queries and optionally downloads Earth Observation products from the
Copernicus Data Space Ecosystem (CDSE) using the OData API.

The user can search products by collection, product name, sensing date,
publication date, product type, orbit information, cloud cover, and spatial
footprint using a WKT polygon in WGS84 coordinates.

The catalogue search does not require authentication. User credentials are only
requested if the user chooses to download the retrieved products. Downloads are
performed through the CDSE zipper service using an access token generated from
the user's Copernicus Data Space account.

Example
-------
Search Sentinel-5P offline NO2 products over a WKT polygon for August 2020:

    python cdse_download.py \
        -c SENTINEL-5P \
        -n S5P_OFFL_L2__NO2___ \
        -ssd 01082020 \
        -esd 31082020 \
        -f "POLYGON((23.4157 37.7256,24.1118 37.7256,24.1118 38.2250,23.4157 38.2250,23.4157 37.7256))"

Notes
-----
- Dates are expected in DDMMYYYY format.
- Spatial coordinates must be given as longitude latitude.
- A CDSE account is required only for downloading products.
"""

import os
import requests
import pandas as pd
import datetime
import getpass
import argparse
from tqdm import tqdm

# Get an access token from Copernicus Data Space Ecosystem.
# The token is required only for downloading products, not for searching.
def get_access_token(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
        }
    
    try:
        r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
        data=data,
        )
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise Exception(f"Access token creation failed: {e}")
    
    return r.json()["access_token"]
        

# Build the OData filter query based on the selected search parameters.
# The final query is passed to the CDSE catalogue Products endpoint.
def get_filters(collection=None, name=None, sensing_start_date=None, 
                              sensing_end_date=None, publication_start_date=None, 
                              publication_end_date=None, footprint=None, productType=None, 
                              cloudCover=None, orbitDirection=None, orbitNumber=None,
                              order=None, top=None, count=False):

    query = ''
    
    collection_options = [
        'SENTINEL-1', 'SENTINEL-2', 'SENTINEL-3', 'SENTINEL-5P', 'SENTINEL-6', 'SENTINEL-1-RTC', 
        'SMOS', 'ENVISAT', 'LANDSAT-5', 'LANDSAT-7', 'LANDSAT-8', 'COP-DEM', 'TERRAAQUA', 'S2GLC'
        ]
    
    # Check that the requested collection is supported by CDSE.
    if collection in collection_options:
        query = "Collection/Name eq '{}' and ".format(collection)
    else:
        raise Exception('Wrong collection. The collection should be one from the list {}'.format(collection_options)) 
    
    # Filter by product name or part of the product name.
    # Useful for Sentinel-5P products, e.g. S5P_OFFL_L2__NO2___.
    if name:
        query = query + "contains(Name,'{}') and ".format(name)

    # Filter products by sensing/acquisition start date.
    # Date format expected here: DDMMYYYY, e.g. 01082020.    
    if sensing_start_date:
        sensing_start_date = datetime.datetime(year=int(sensing_start_date[4:]), 
                                             month=int(sensing_start_date[2:4]), 
                                             day=int(sensing_start_date[:2]))
        query = query + "ContentDate/Start gt {}.000Z and ".format(sensing_start_date.isoformat())

    # Filter products by sensing/acquisition end date.
    # The time is set to the end of the selected day.    
    if sensing_end_date:
        sensing_end_date = datetime.datetime(year=int(sensing_end_date[4:]), 
                                             month=int(sensing_end_date[2:4]), 
                                             day=int(sensing_end_date[:2]), 
                                             hour=23, minute=59, second=59)
        query = query + "ContentDate/Start lt {}.999Z and ".format(sensing_end_date.isoformat())
        
    # Filter products by publication date in the CDSE catalogue.
    if publication_start_date:
        publication_start_date = datetime.datetime(year=int(publication_start_date[4:]), 
                                             month=int(publication_start_date[2:4]), 
                                             day=int(publication_start_date[:2]))
        query = query + "PublicationDate gt {}.000Z and ".format(publication_start_date.isoformat())

    if publication_end_date:
        publication_end_date = datetime.datetime(year=int(publication_end_date[4:]), 
                                             month=int(publication_end_date[2:4]), 
                                             day=int(publication_end_date[:2]), 
                                             hour=23, minute=59, second=59)
        query = query + "PublicationDate lt {}.999Z and ".format(publication_end_date.isoformat())
        
    # Spatial filter using a WKT polygon in WGS84 coordinates.
    # Example: POLYGON((lon lat, lon lat, lon lat, lon lat, lon lat))    
    if footprint: #polygon wkt wgs84
        query = query + "OData.CSC.Intersects(area=geography'SRID=4326;{}') and ".format(footprint) 

    # Filter by product type when this attribute exists in the collection.
    # Example for Sentinel-1: IW_SLC__1SDV.
    if productType:
        query = query + "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{}') and ".format(productType)

    # Filter by orbit direction, e.g. ASCENDING or DESCENDING.
    if orbitDirection:
        query = query + "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq '{}') and ".format(orbitDirection)

    # Filter by relative/absolute orbit number, depending on the collection metadata.
    if orbitNumber:
        query = query + "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'orbitNumber' and att/OData.CSC.DoubleAttribute/Value eq {}) and ".format(orbitNumber)
        
    # Filter by cloud cover. Here the query keeps products with cloudCover <= selected value.        
    if cloudCover:
        query = query + "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {}) and ".format(cloudCover)

    query = query[:-5] #trim last ' and '
    
    if order:
        query = query + "&$orderby=" + order
        
    if top:
        query = query + "&$top={}".format(top)
        
    if count:
        query = query + "&$count=True"
        
        
    return query


# Send the OData query to the CDSE catalogue and return the results as a pandas DataFrame.
def get_product_list(query):
    
    url = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter={}".format(query)
    
    # Request product metadata from the catalogue.
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    js = r.json()
    
    # Convert the returned JSON product list into a table.    
    df = pd.DataFrame.from_dict(js['value'])

    # # Print only specific columns
    # columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
    # df[columns_to_print].head(3)
    
    return df
    

# Download all products listed in the DataFrame using the authenticated CDSE zipper service.
# Download all products listed in the DataFrame using the authenticated CDSE zipper service.
def download_datasets(access_token: str, df, output_dir=None):
    
    # If no output folder is given, save files in the current working directory.
    if output_dir is None:
        output_dir = os.getcwd()

    os.makedirs(output_dir, exist_ok=True)

    for i, (name, id_) in enumerate(zip(df["Name"], df["Id"]), start=1):

        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({id_})/$value"
        output_path = os.path.join(output_dir, f"{name}.zip")

        print(f"\n[{i}/{len(df)}] Downloading product:")
        print(f"  {name}")
        print(f"Saving to:")
        print(f"  {output_path}")

        headers = {"Authorization": f"Bearer {access_token}"}

        session = requests.Session()
        session.headers.update(headers)

        response = session.get(url, headers=headers, stream=True)

        if response.status_code == 401:
            access_token = get_access_token(username, password)

            headers = {"Authorization": f"Bearer {access_token}"}
            session.headers.update(headers)

            response = session.get(url, headers=headers, stream=True)

        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))

        with open(output_path, "wb") as file:
            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc="Progress"
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
                        progress_bar.update(len(chunk))

        print(f"Finished downloading: {output_path}")                    


#Chile
#POLYGON((-68.126221 -25.869109,-68.126221 -20.786931,-67.664795 -20.786931,-67.664795 -25.869109,-68.126221 -25.869109))



if __name__ == "__main__":
    # Define command-line arguments for catalogue search and optional download.
    parser = argparse.ArgumentParser(
        description="Query and Download Copernicus data from the Copernicus DataSpace using the ODATA API. " +
                    "You need to be registered to Copernicus DataSpace and use your credentials to access the API."
    )
    
    # Read command-line arguments.
    parser.add_argument("-c", required=True, type=str, help='Collection')
    parser.add_argument("-n", required=False, type=str, help='Name or part of it')
    parser.add_argument("-ssd", required=False, type=str, help='Start for Sensing Date')
    parser.add_argument("-esd", required=False, type=str, help='End for Sensing Date')
    parser.add_argument("-spd", required=False, type=str, help='Start for Publication Date')
    parser.add_argument("-epd", required=False, type=str, help='End for Publication Date')
    parser.add_argument("-f", required=False, type=str, help='Polygon in WKT in WGS84')
    parser.add_argument("-p", required=False, type=str, help='productType (e.g. AUX_POEORB, IW_SLC__1SDV)')
    parser.add_argument("-cc", required=False, type=str, help='Cloud Cover')
    parser.add_argument("-od", required=False, type=str, help='Orbit Direction')
    parser.add_argument("-on", required=False, type=int, help='Orbit Number')
    parser.add_argument("-o", required=False, type=str, help='Order')
    parser.add_argument("-top", required=False, type=int, help='Number of results returned. Defautl 20')
    parser.add_argument("-count", required=False, type=str)
    args = parser.parse_args()

    # Build the catalogue search filter from the selected arguments.
    collection = args.c # "SENTINEL-1"
    name = args.n # e.g. S1B
    sensing_start_date = args.ssd #e.g. 10112017
    sensing_end_date = args.esd
    publication_start_date = args.spd
    publication_end_date = args.epd
    footprint = args.f
    productType = args.p # e.g. AUX_POEORB, IW_SLC__1SDV
    cloudCover = args.cc
    orbitDirection = args.od
    orbitNumber = args.on
    order = args.o
    top = args.top
    count = args.count
    
   
    # access_token = get_access_token(
    #     getpass.getpass("Enter your username"),
    #     getpass.getpass("Enter your password"),
    #     )
    
    filters = get_filters(collection=collection, name=name, sensing_start_date=sensing_start_date, 
                                  sensing_end_date=sensing_end_date, publication_start_date=publication_start_date, 
                                  publication_end_date=publication_end_date, footprint=footprint, productType=productType, 
                                  cloudCover=cloudCover, orbitDirection=orbitDirection, orbitNumber=orbitNumber, 
                                  order=order, top=top, count=False)
    
    # Search the CDSE catalogue and retrieve matching products.
    product_list = get_product_list(filters)
    
    # Print the product names so the user can decide whether to download them.
    print(product_list.Name)
    print('')
    
    # Ask the user whether to download the retrieved products.
    print('Would you like to download the retrieved files? [Y/n]')
    
    answer = input()
    
    if answer in ['y', 'Y', '']:
        
        # get credencials for Copernicus Data Space Ecosystem 
        # Credentials are requested only if download is selected.
        print('Enter your username: ', end="")
        username = input() # e.g. email@gmail.com
        print('Enter your password: ', end="")
        password = getpass.getpass("Enter your password: ") # dataspace_password
        
        access_token = get_access_token(username, password)
        
        download_datasets(access_token, product_list)
        
    else:
        	print('No file will be downloaded.')


