import json
import logging
from pathlib import Path
import re
import unicodedata

import geopandas as gpd
import psycopg
from rich.table import Table
from rich.text import Text
from shapely.geometry import Polygon

from coord_buffer_cli.config import (
    BUFFER_MULTIPLIER,
    DB_PARAMS,
    DEFAULT_EPSG,
    METRIC_EPSG,
    console,
)


def print_coordinates(coord_dataframe):
    for _, row in coord_dataframe.iterrows():
        dms = to_dms_coords([row["y"], row["x"]])
        lat, lon = dms.split()
        line = Text.assemble((lat, "yellow"), (" ", ""), (lon, "cyan"))
        console.print(line)


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

        features_coord = []

        for feature in geojson_data["features"]:
            nameofarea = (
                feature.get("properties", {}).get("NAME")
                or feature.get("properties", {}).get("name")
                or Path(filename).stem
            )

            geometry = feature.get("geometry", {})
            if geometry.get("type") != "Polygon":
                raise ValueError(f"Unsupported geometry type: {geometry.get('type')}")

            coords = []
            for polygon in geometry.get("coordinates", []):
                for coord in polygon:
                    if not isinstance(coord, list) or len(coord) != 2:
                        raise ValueError(f"Invalid coordinate format: {coord}")
                    coords.append(coord)
            features_coord.append((coords, nameofarea))
        return features_coord


def get_last_update():
    query = """
        SELECT wef
        FROM aip_data
    """
    with psycopg.connect(**DB_PARAMS) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()

            if not rows:
                raise ValueError("Missing last updated date")

            dates = set(row[0] for row in rows)

            if len(dates) > 1:
                logging.warning(f"Multiple last updated dates found: {dates}")
            else:
                dates = dates.pop()
            return dates


def list_coords_from_db():
    last_update = get_last_update()
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

            table = Table(
                title=f"Available TMAs{f' - Last Updated {last_update if last_update else ""}'}",
                header_style="bold magenta",
            )
            table.add_column("MSID", style="cyan", justify="center")
            table.add_column("TMA", style="green", justify="left")

            for (
                msid,
                name,
            ) in rows:
                table.add_row(str(msid), name)
            console.print(table)
            return rows


def read_coords_from_db(msid):
    query = """
        SELECT ST_AsGeoJSON(geom) as geojson, nameofarea
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
            tma_name = rows[0][1]
            return geojson["coordinates"][0], tma_name
