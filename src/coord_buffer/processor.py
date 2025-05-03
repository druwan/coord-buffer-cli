import json
import os
from datetime import datetime

import geopandas as gpd
import psycopg
from shapely.geometry import Polygon

from coord_buffer.config import BUFFER_MULTIPLIER, DB_PARAMS, DEFAULT_EPSG, METRIC_EPSG
from coord_buffer.utils import clean_file_name


def create_geojson_files(geo_df, folder_name):
    """Create individual GeoJSON files for each TMA."""
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
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
    """Buffer a polygon by a distance in nautical miles."""
    gdf = gpd.GeoDataFrame(geometry=[Polygon(coords)], crs=f"EPSG:{DEFAULT_EPSG}")
    gdf = gdf.to_crs(epsg=METRIC_EPSG)
    buffered = gdf.buffer(
        distance=buffer_size_nm * BUFFER_MULTIPLIER, single_sided=True, join_style=2
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


def insert_tmas_to_db(geo_df, conn_params=DB_PARAMS):
    """Insert TMA GeoJSON features into PostgreSQL database."""
    conn = None
    try:
        conn = psycopg.connect(**conn_params)
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO tmas (
                name_of_area, geometry, wef, type_of_area, position_indicator,
                date_time_of_chg, name_of_operator, origin, location,
                upper_limit, lower_limit, comment_1, comment_2, quality,
                crc_id, crc_pos, crc_tot, msid, idnr, mi_style, updated_at
            ) VALUES (
                %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (name_of_area, wef)
            DO UPDATE SET
                geometry = EXCLUDED.geometry,
                type_of_area = EXCLUDED.type_of_area,
                position_indicator = EXCLUDED.position_indicator,
                date_time_of_chg = EXCLUDED.date_time_of_chg,
                name_of_operator = EXCLUDED.name_of_operator,
                origin = EXCLUDED.origin,
                location = EXCLUDED.location,
                upper_limit = EXCLUDED.upper_limit,
                lower_limit = EXCLUDED.lower_limit,
                comment_1 = EXCLUDED.comment_1,
                comment_2 = EXCLUDED.comment_2,
                quality = EXCLUDED.quality,
                crc_id = EXCLUDED.crc_id,
                crc_pos = EXCLUDED.crc_pos,
                crc_tot = EXCLUDED.crc_tot,
                msid = EXCLUDED.msid,
                idnr = EXCLUDED.idnr,
                mi_style = EXCLUDED.mi_style,
                updated_at = CURRENT_TIMESTAMP
        """

        for _, row in geo_df.iterrows():
            name = clean_file_name(row["NAMEOFAREA"])
            if "TMA_" in name:
                continue

            geometry_series = gpd.GeoSeries(
                [row["geometry"]], crs=f"EPSG:{DEFAULT_EPSG}"
            )
            geometry_json = geometry_series.to_json()
            feature_geometry = json.loads(geometry_json)["features"][0]["geometry"]

            properties = row.to_dict()
            wef = properties.get("WEF")
            if wef:
                try:
                    wef = datetime.strptime(wef, "%Y-%m-%d").date()
                except ValueError:
                    wef = None

            cursor.execute(
                insert_query,
                (
                    name,
                    json.dumps(feature_geometry),
                    wef,
                    properties.get("TYPEOFAREA"),
                    properties.get("POSITIONINDICATOR"),
                    properties.get("DATETIMEOFCHG"),
                    properties.get("NAMEOFOPERATOR"),
                    properties.get("ORIGIN"),
                    properties.get("LOCATION"),
                    properties.get("UPPER"),
                    properties.get("LOWER"),
                    properties.get("COMMENT_1"),
                    properties.get("COMMENT_2"),
                    properties.get("QUALITY"),
                    properties.get("CRC_ID"),
                    properties.get("CRC_POS"),
                    properties.get("CRC_TOT"),
                    properties.get("MSID"),
                    properties.get("IDNR"),
                    properties.get("MI_STYLE"),
                ),
            )

        conn.commit()
        cursor.close()
    except Exception as e:
        if conn:
            conn.rollback()
        raise RuntimeError(f"Failed to insert TMAs into database: {e}")
    finally:
        if conn:
            conn.close()


def get_latest_airac_date(conn_params):
    """Get the latest AIRAC effective date from the database."""
    conn = None
    try:
        conn = psycopg.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(wef) FROM tmas")
        latest_wef = cursor.fetchone()[0]
        cursor.close()
        return latest_wef
    except Exception as e:
        raise RuntimeError(f"Failed to fetch latest AIRAC date: {e}")
    finally:
        if conn:
            conn.close()


def is_airac_current(conn_params, airac_date):
    """Check if the provided AIRAC date is the latest in the database."""
    latest_wef = get_latest_airac_date(conn_params)
    if not latest_wef:
        return False
    try:
        airac_date = datetime.strptime(airac_date, "%Y-%m-%d").date()
        return airac_date >= latest_wef
    except ValueError:
        raise ValueError("Invalid AIRAC date format, expected YYYY-MM-DD")
