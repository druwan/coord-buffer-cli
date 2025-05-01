import json
import os
import sys
from io import BytesIO

import geopandas as gpd
import requests
from shapely.geometry import Polygon

# Constants
BUFFER_MULTIPLIER = 1852
DEFAULT_EPSG = 4326  # WGS84
METRIC_EPSG = 3006


def fetch_tmas(EPSG=DEFAULT_EPSG):
    """
    Fetch TMAs from echarts
    """
    url = f"https://daim.lfv.se/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=mais:TMAS,mais:TMAW&undefined=&outputFormat=application/json&srsName=EPSG:{EPSG}"
    resp = requests.get(url)
    if resp.status_code == 200:
        return resp.content
    else:
        raise ValueError("Error fetching TMAs")


def to_wgs84(geo_df):
    """ "
    Convert to WGS84 crs
    """
    return geo_df.to_crs(epsg=DEFAULT_EPSG)


def create_geojson_files(geo_df, folder_name):
    for idx, row in geo_df.iterrows():
        name_of_area = (
            row["NAMEOFAREA"]
            .replace(" ", "_")
            .replace("Å", "A")
            .replace("Ä", "A")
            .replace("Ö", "O")
            .upper()
        )
        geometry = row["geometry"]
        single_gdf = gpd.GeoDataFrame(
            {"NAMEOFAREA": [name_of_area], "geometry": [geometry]}, crs="EPSG:4326"
        )

        filename = f"{folder_name}/{name_of_area}.geojson"
        single_gdf.to_file(filename, driver="GeoJSON")


def buffer_in_NM(buffer_distance):
    """
    Take the Distance in Nautical Miles and returns it in Meters
    """
    return buffer_distance * BUFFER_MULTIPLIER


def dms_to_dd_coords(coord):
    """
    Convert DMS to DD
    """
    if len(coord) > 7:
        coord = coord[1:]
    degrees = int(coord[:2])
    minutes = int(coord[2:4])
    seconds = int(coord[4:6])
    direction = coord[6]

    dd = degrees + minutes / 60 + seconds / 3600
    return dd if direction in ["N", "E"] else -dd


def dd_to_dms(coord):
    degrees = int(coord)
    minutes = (coord - degrees) * 60
    seconds = (minutes - int(minutes)) * 60
    return f"{degrees:02d}{int(minutes):02d}{int(seconds):02d}"


def to_dms_coords(coord):
    lat, lon = coord
    return f"{dd_to_dms(lat)}N 0{dd_to_dms(lon)}E"


def read_coords(filename):
    """
    Read coords from file
    """
    with open(filename, "r") as file:
        geojson_data = json.load(file)
        coords = []
        for feature in geojson_data["features"]:
            geom_type = feature["geometry"]["type"]
            geom_coords = feature["geometry"]["coordinates"]
            if geom_type == "Polygon":
                for polygon in geom_coords:
                    for coord in polygon:
                        coords.append(coord)
        return coords


def main():
    folder_name = "POLYGONES"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    try:
        tmas = fetch_tmas()
        tma_gdf_3857 = gpd.read_file(BytesIO(tmas))
        gma_gdf_4326 = to_wgs84(tma_gdf_3857)
        create_geojson_files(gma_gdf_4326, folder_name)
    except Exception as e:
        print(f"Error fetching or processing TMA data: {e}")
        sys.exit(1)

    # Check if coord file exists
    try:
        filename = sys.argv[1]
        buffer_size_nm = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    except IndexError:
        print("Requires an input file with coords")
        exit(0)

    coords_dd = read_coords(filename)

    # Create the polygon
    polygon_gdf = gpd.GeoDataFrame(geometry=[Polygon(coords_dd)], crs="EPSG:4326")

    # Reproject it with meters
    polygon_gdf = polygon_gdf.to_crs(epsg=METRIC_EPSG)

    # Add buffer
    polygon_gdf_buffered = polygon_gdf.buffer(
        distance=buffer_in_NM(buffer_size_nm), single_sided=True, join_style=2
    )

    # Reproject it back into latlong
    newBufferPolygon = polygon_gdf_buffered.to_crs(epsg=DEFAULT_EPSG)

    # Save the buffered coordinates
    bufferedlonLatCoords = []
    coordDF = newBufferPolygon.get_coordinates()
    for _, row in coordDF.iterrows():
        latitude, longitude = row.iloc[0], row.iloc[1]
        bufferedlonLatCoords.append([longitude, latitude])

    # Convert and print the result
    [print(to_dms_coords(coord)) for coord in bufferedlonLatCoords]


if __name__ == "__main__":
    main()
