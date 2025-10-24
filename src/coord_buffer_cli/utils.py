import json
import logging
import re
import unicodedata

import geopandas as gpd
import psycopg
from shapely.geometry import Polygon
from tabulate import tabulate

from coord_buffer_cli.config import (
    BUFFER_MULTIPLIER,
    DB_PARAMS,
    DEFAULT_EPSG,
    METRIC_EPSG,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_file_name(name):
    name = unicodedata.normalize("NFKD", name)
    name = name.strip()
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"\s+", "_", name)
    return name.upper()


def dms_to_dd_coords(coord):
    if not re.match(r"^\d{6}[NSEW]$", coord):
        raise ValueError(f"Invalid DMS format: {coord}")
    degrees, minutes, seconds = int(coord[:2]), int(coord[2:4]), int(coord[4:6])
    direction = coord[6]
    dd = degrees + minutes / 60 + seconds / 3600
    return dd if direction in ["N", "E"] else -dd


def dd_to_dms(coord):
    degrees = int(abs(coord))
    minutes = (abs(coord) - degrees) * 60
    seconds = (minutes - int(minutes)) * 60
    return f"{degrees:02d}{int(minutes):02d}{int(seconds):02d}"


def to_dms_coords(coord):
    lat, lon = coord
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{dd_to_dms(lat)}{lat_dir} 0{dd_to_dms(lon)}{lon_dir}"


def to_wgs84(geo_df):
    return geo_df.to_crs(epsg=DEFAULT_EPSG)


def buffer_polygon(coords, buffer_size_nm):
    """Buffer a polygon by a distance in nautical miles."""
    gdf = gpd.GeoDataFrame(geometry=[Polygon(coords)], crs=f"EPSG:{DEFAULT_EPSG}")
    gdf = gdf.to_crs(epsg=METRIC_EPSG)
    buffered = gdf.buffer(
        distance=buffer_size_nm * BUFFER_MULTIPLIER,
        single_sided=True,
        join_style="mitre",
    )
    return buffered.to_crs(epsg=DEFAULT_EPSG)


def read_coords(filename):
    """Read coordinates from a GeoJSON file."""
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
                    if not isinstance(coord, list) or len(coord) != 2:
                        raise ValueError(f"Invalid coordinate format: {coord}")
                    coords.append(coord)
        return coords


def list_coords_from_db():
    query = """
        SELECT msid, nameofarea
        FROM aip_data
        WHERE typeofarea = 'TMAW'
        ORDER BY nameofarea;
    """
    with psycopg.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
            if not rows:
                raise ValueError("No geometries found")

            print(
                tabulate(
                    rows, headers=["MSID", "TMA"], tablefmt="pretty", colalign=("left",)
                )
            )
            return rows


def read_coords_from_db(msid):
    query = """
        SELECT ST_AsGeoJSON(geom) as geojson
        FROM aip_data
        where msid = %s;
    """
    with psycopg.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(query, (msid,))
            rows = cur.fetchall()
            if not rows:
                raise ValueError("Error: No geometry found for the given MSID")

            geojson_str = rows[0][0]
            geojson = json.loads(geojson_str)
            return geojson["coordinates"][0]
