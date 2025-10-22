#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  8 13:58:45 2023

@author: pelagia
"""

############################################################################
#
#
#
############################################################################

import json
import requests
import pandas as pd
import datetime
import getpass
import argparse




# Get Access Token from user account 
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
    except:
        raise Exception(
            f"Access token creation failed. Reponse from the server was: {r.json()}"
            )
    
    return r.json()["access_token"]
        

# 
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
    

    if collection in collection_options:
        query = "Collection/Name eq '{}' and ".format(collection)
    else:
        raise Exception('Wrong collection. The collection should be one from the list {}'.format(collection_options)) 
    
    if name:
        query = query + "contains(Name,'{}') and ".format(name)
    
    
    if sensing_start_date:
        sensing_start_date = datetime.datetime(year=int(sensing_start_date[6:]), 
                                             month=int(sensing_start_date[3:5]), 
                                             day=int(sensing_start_date[:2]))
        query = query + "ContentDate/Start gt {}.000Z and ".format(sensing_start_date.isoformat())
    
    
    if sensing_end_date:
        sensing_end_date = datetime.datetime(year=int(sensing_end_date[6:]), 
                                             month=int(sensing_end_date[3:5]), 
                                             day=int(sensing_end_date[:2]), 
                                             hour=23, minute=59, second=59)
        query = query + "ContentDate/Start lt {}.999Z and ".format(sensing_end_date.isoformat())
        
        
    if publication_start_date:
        publication_start_date = datetime.datetime(year=int(publication_start_date[6:]), 
                                             month=int(publication_start_date[4:5]), 
                                             day=int(publication_start_date[:2]))
        query = query + "PublicationDate gt {}.000Z and ".format(publication_start_date.isoformat())

        
    if publication_end_date:
        publication_end_date = datetime.datetime(year=int(publication_end_date[6:]), 
                                             month=int(publication_end_date[4:5]), 
                                             day=int(publication_end_date[:2]), 
                                             hour=23, minute=59, second=59)
        query = query + "PublicationDate lt {}.999Z and ".format(publication_end_date.isoformat())
        
    
    if footprint: #polygon wkt wgs84
        query = query + "OData.CSC.Intersects(area=geography'SRID=4326;{}') and ".format(footprint) 


    if productType:
        query = query + "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{}') and ".format(productType)


    if orbitDirection:
        query = query + "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'orbitDirection' and att/OData.CSC.StringAttribute/Value eq '{}') and ".format(orbitDirection)

    if orbitNumber:
        query = query + "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'orbitNumber' and att/OData.CSC.DoubleAttribute/Value eq '{}') and ".format(orbitNumber)
        
        
    if cloudCover:
        query = query + "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value eq/le/lt/ge/gt '{}') and ".format(cloudCover)


    query = query[:-5] #trim last ' and '
    
    if order:
        query = query + "&$orderby=" + order
        
        
    if top:
        query = query + "&$top={}".format(top)
        
        
    if count:
        query = query + "&$count=True"
        
        
    return query


def get_product_list(query):
    
    js = requests.get("https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter={}".format(query)).json()
    df = pd.DataFrame.from_dict(js['value'])

    # # Print only specific columns
    # columns_to_print = ['Id', 'Name','S3Path','GeoFootprint']  
    # df[columns_to_print].head(3)
    
    return df
    

def download_datasets(access_token:str, df):
   
    for name, id_ in zip(df['Name'], df['Id']):     
        
        url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({id_})/$value"
       
        headers = {"Authorization": f"Bearer {access_token}"}

        session = requests.Session()
        session.headers.update(headers)
        
        response = session.get(url, headers=headers, stream=True)
        
        if response.status_code == 401:
            access_token = get_access_token(username, password)
            
            headers = {"Authorization": f"Bearer {access_token}"}
            
            session = requests.Session()
            session.headers.update(headers)
            
            response = session.get(url, headers=headers, stream=True)

        with open(f"{name}.zip", "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    


#Chile
#POLYGON((-68.126221 -25.869109,-68.126221 -20.786931,-67.664795 -20.786931,-67.664795 -25.869109,-68.126221 -25.869109))






if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Query and Download Copernicus data from the Copernicus DataSpace using the ODATA API. " +
                    "You need to be registered to Copernicus DataSpace and use your credentials to access the API."
    )
    
    parser.add_argument("-c", required=True, type=str, help='Collection')
    parser.add_argument("-n", required=False, type=str, help='Name or part of it')
    parser.add_argument("-ssd", required=False, type=str, help='Start for Sensing Date')
    parser.add_argument("-esd", required=False, type=str, help='End for Sensing Date')
    parser.add_argument("-spd", required=False, type=str, help='Start for Publication Date')
    parser.add_argument("-epd", required=False, type=str, help='End for Publication Date')
    parser.add_argument("-f", required=False, type=str, help='Polygon in WTK in WGS84')
    parser.add_argument("-p", required=False, type=str, help='productType (e.g. AUX_POEORB, IW_SLC__1SDV)')
    parser.add_argument("-cc", required=False, type=str, help='Cloud Cover')
    parser.add_argument("-od", required=False, type=str, help='Orbit Direction')
    parser.add_argument("-on", required=False, type=int, help='Orbit Number')
    parser.add_argument("-o", required=False, type=str, help='Order')
    parser.add_argument("-top", required=False, type=int, help='Number of results returned. Defautl 20')
    parser.add_argument("-count", required=False, type=str)
    args = parser.parse_args()

    collection = args.c # "SENTINEL-1"
    name = args.n # e.g. S1B
    sensing_start_date = args.ssd #e.g. 10/11/2017
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
    
    # get credencials for Copernicus Data Space Ecosystem 
    print('Enter your username: ', end="")
    username = input() # e.g. email@gmail.com
    print('Enter your password: ', end="")
    password = input() # dataspace_password
    
    
    # access_token = get_access_token(
    #     getpass.getpass("Enter your username"),
    #     getpass.getpass("Enter your password"),
    #     )
    
    access_token = get_access_token(username, password)
    
    filters = get_filters(collection=collection, name=name, sensing_start_date=sensing_start_date, 
                                  sensing_end_date=sensing_end_date, publication_start_date=publication_start_date, 
                                  publication_end_date=publication_end_date, footprint=footprint, productType=productType, 
                                  cloudCover=cloudCover, orbitDirection=orbitDirection, orbitNumber=orbitNumber, 
                                  order=order, top=top, count=False)
    
    product_list = get_product_list(filters)
    
    print(product_list.Name)
    print('')
    print('Would you like to download the retrieved files? [Y/n]')
    answer = input()
    if answer in ['y', 'Y', '']:
    	download_datasets(access_token, product_list)
    else:
    	print('No file will be downloaded.')



























