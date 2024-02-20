#!/usr/bin/python3

import sys
from shapely.geometry import Polygon
from shapely.ops import transform
import pyproj
from functools import partial


def dmsToDecDeg(coord):
    if len(coord) > 7:
        coord = coord[1:]
    degrees = int(coord[:2])
    minutes = int(coord[2:4])
    seconds = int(coord[4:6])
    direction = coord[6]

    dd = degrees + minutes / 60 + seconds / 3600
    return dd if direction in ["N", "E"] else -dd


def createPolygon(coords):
    # Convert DMS coords to decimal degree
    dd_coords = [(dmsToDecDeg(coord[:7]), dmsToDecDeg(coord[8:])) for coord in coords]
    # Create Shapely Polygon
    poly = Polygon(dd_coords)
    # Set up CRS
    wgs84 = pyproj.CRS("epsg:4326")
    projection = partial(pyproj.transform, wgs84, wgs84)
    # Project WGS onto OG Polygon
    polygon = transform(projection, poly)
    return polygon


def nmToDD(buffer_range):
    # Create the range in decimal degrees, approximation!
    return buffer_range / 60


def addBufferToPolygon(polygon, bufferSize):
    bufferPolygon = polygon.buffer(
        nmToDD(bufferSize), join_style="mitre", mitre_limit=2
    )
    wgs84 = pyproj.CRS("epsg:4326")
    projection = partial(pyproj.transform, wgs84, wgs84)
    bufferedPolygon = transform(projection, bufferPolygon)
    return bufferedPolygon


def decDegToDMS(coord):
    degrees = int(coord)
    minutes = (coord - degrees) * 60
    seconds = (minutes - int(minutes)) * 60
    return f"{degrees:02d}{int(minutes):02d}{int(seconds):02d}"


def decDegToDMSString(coord):
    lat = coord[0]
    lon = coord[1]
    return f"{decDegToDMS(lat)}N 0{decDegToDMS(lon)}E"


def readCoords(filename):
    with open(filename, "r") as file:
        return [(line.strip()) for line in file]


def main():
    # Check if coord file exists
    try:
        filename = sys.argv[1]
        # Check for custom buffer
        try:
            bufferSize = int(sys.argv[2])
        except IndexError:
            bufferSize = 0
            print("No custom buffer range, defaulting to 0")
    except IndexError:
        print(f"Requires an input file with coords")
        exit(0)

    # Read coordinates from the file
    coordsDMS = readCoords(filename)

    # Create a Shapely polygon from DMS coordinates
    polygonOG = createPolygon(coordsDMS)

    # Add a buffer to the polygon
    bufferedPolygon = addBufferToPolygon(polygonOG, bufferSize)

    # Get the exterior coordinates of the buffered polygon
    bufferedCoordsOut = list(bufferedPolygon.exterior.coords)

    # Convert buffered coordinates to DMS format
    bufferedCoordsDMS = [decDegToDMSString(coord) for coord in bufferedCoordsOut]

    # Print the buffered coordinates
    for coord in bufferedCoordsDMS:
        print(coord)


if __name__ == "__main__":
    main()
