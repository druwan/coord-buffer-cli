import sys
from shapely.geometry import Polygon
import geopandas as gpd


def toDecDegCoords(coord):
    if len(coord) > 7:
        coord = coord[1:]
    degrees = int(coord[:2])
    minutes = int(coord[2:4])
    seconds = int(coord[4:6])
    direction = coord[6]

    dd = degrees + minutes / 60 + seconds / 3600
    return dd if direction in ["N", "E"] else -dd


def decDegToDMS(coord):
    degrees = int(coord)
    minutes = (coord - degrees) * 60
    seconds = (minutes - int(minutes)) * 60
    return f"{degrees:02d}{int(minutes):02d}{int(seconds):02d}"


def toDMSCoords(coord):
    lat = coord[0]
    lon = coord[1]
    return f"{decDegToDMS(lat)}N 0{decDegToDMS(lon)}E"


def readCoords(filename):
    with open(filename, "r") as file:
        return [(line.strip()) for line in file]


def bufferInNm(bufferDistance):
    """
    Take the Distance in Nautical Miles and returns it in Meters
    """
    return bufferDistance * 1852 * 2


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
    # Save them in decimal degree
    latLonDdCoords = [
        (toDecDegCoords(coords[:7]), toDecDegCoords(coords[8:])) for coords in coordsDMS
    ]
    # Reordered for GeoPandas
    lonLatDdCoords = [
        [toDecDegCoords(coords[8:]), toDecDegCoords(coords[:7])] for coords in coordsDMS
    ]

    # Create the polygon
    geoPandasPolygon = gpd.GeoDataFrame(
        index=[0], geometry=[Polygon(lonLatDdCoords)], crs="EPSG:4326"
    )
    # Reproject it with meters
    geoPandasPolygon = geoPandasPolygon.to_crs(epsg=3857)
    # Add buffer
    geoPandasPolygonBuffered = geoPandasPolygon.buffer(
        distance=bufferInNm(bufferSize), join_style=2
    )

    # Reproject it back into latlong
    newBufferPolygon = geoPandasPolygonBuffered.to_crs(epsg=4326)

    # Save the buffered coordinates
    bufferedlonLatCoords = []
    coordDF = newBufferPolygon.get_coordinates()
    for idx, row in coordDF.iterrows():
        latitude, longitude = row[idx], row[idx + 1]
        bufferedlonLatCoords.append([longitude, latitude])

    # Convert and print the result
    [print(toDMSCoords(coord)) for coord in bufferedlonLatCoords]


if __name__ == "__main__":
    main()
