#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 15 12:17:38 2025

@author: pelagia
"""

import pygmt

#def make_aoi_map(feature_path):
    
x = [25.732335783844334, 25.92890398843026, 27.376314075981746, 27.14416308185329, 25.732335783844334]
y = [67.11374187687282, 67.71396519054159, 67.63897836500453, 67.03867287399272, 67.11374187687282]

point = (26.5900744, 67.4189270)

# Set the region of the main figure
region = [23, 30, 65, 69]

fig = pygmt.Figure()


# grid = pygmt.datasets.load_earth_relief(resolution="10m", region=region)

# fig.grdimage(grid=grid, frame="a", cmap="geo")
fig.coast(region=region, projection="M10c", land="lightgray", water="lightblue", borders="1/0.5p", shorelines="1/0.5p", frame="ag")

font = "11p,Helvetica-Bold"
fig.plot(x=point[0], y=point[1], style="a0.2c", pen="1.5p,gray40")
fig.text(x=point[0]+0.7, y=point[1] + 0.1, text="Sodankylä", font=font)


with fig.inset(position="jTR+w4c+o0.1c", margin=0, box="+p1p,black"):
    # Create a figure in the inset using coast. This example uses the azimuthal
    # orthogonal projection centered at 47E, 20S. The land color is set to
    # "gray" and Madagascar is highlighted in "red3".
    fig.coast(
        region="g",
        projection="G30/40/?",
        land="gray",
        water="white",
        dcw="FI+gred3",
    )

fig.plot(x=x, y=y, pen="2p,red")

fig.show()