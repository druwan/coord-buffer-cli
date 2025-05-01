import json

import geopandas as gpd
from shapely.geometry import Polygon

from .config import BUFFER_MULTIPLIER, DEFAULT_EPSG, METRIC_EPSG
from .utils import clean_file_name


def create_geojson_files(geo_df, folder_name):
    for _, row in geo_df.iterrows():
        name = clean_file_name(row["NAMEOFAREA"])
        if "TMA_" in name:
            continue
        single_gdf = gpd.GeoDataFrame(
            {"NAMEOFAREA": [name], "geometry": [row["geometry"]]},
            crs=f"EPSG:{DEFAULT_EPSG}",
        )

        filename = f"{folder_name}/{name}.geojson"
        single_gdf.to_file(filename, driver="GeoJSON")


def buffer_polygon(coords, buffer_size_nm):
    gdf = gpd.GeoDataFrame(geometry=[Polygon(coords)], crs=f"EPSG:{DEFAULT_EPSG}")
    gdf = gdf.to_crs(epsg=METRIC_EPSG)
    buffered = gdf.buffer(
        distance=buffer_size_nm * BUFFER_MULTIPLIER, single_sided=True, join_style=2
    )
    return buffered.to_crs(epsg=DEFAULT_EPSG)


def read_coords(filename):
    with open(filename, "r") as file:
        geojson_data = json.load(file)
        if not geojson_data.get("features"):
            raise ValueError("GeoJSON file has no features")
        coords = []
        for feature in geojson_data["features"]:
            if feature["geometry"]["type"] != "Polygon":
                raise ValueError(
                    f"Unsupported geometry type: {feature['geometry']['type']}"
                )
            for polygon in feature["geometry"]["coordinates"]:
                for coord in polygon:
                    coords.append(coord)
        return coords
