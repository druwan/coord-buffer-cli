import sys
from shapely.geometry import Polygon
import utm


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


def bufferInNm(bufferSize):
    return bufferSize * 1852


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

    utmCoords = []
    # Convert & Save as UTM format
    for point in latLonDdCoords:
        easting, northing, zone_number, zone_letter = utm.from_latlon(
            point[0], point[1]
        )
        utmCoords.append((easting, northing, zone_number, zone_letter))

    # Create the polygon
    utmPolygon = Polygon(tuple(utmCoords[0:1]))
    # Add buffer
    bufferedPolygon = utmPolygon.buffer(
        distance=bufferInNm(bufferSize), cap_style="square", join_style="mitre"
    )

    # Save the buffered coordinates
    bufferedUTMCoords = []
    for point in list(bufferedPolygon.exterior.coords):
        latitude, longitude = utm.to_latlon(
            point[0], point[1], zone_number, zone_letter
        )
        bufferedUTMCoords.append([latitude, longitude])

    # Convert and print the result
    [print(toDMSCoords(coord)) for coord in bufferedUTMCoords]


if __name__ == "__main__":
    main()
