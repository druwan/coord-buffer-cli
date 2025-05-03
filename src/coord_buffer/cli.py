import argparse
import os
import sys
from io import BytesIO

import geopandas as gpd

from coord_buffer.config import DB_PARAMS, OUTPUT_FOLDER
from coord_buffer.coords import to_dms_coords, to_wgs84
from coord_buffer.fetcher import fetch_tmas
from coord_buffer.processor import (
    buffer_polygon,
    create_geojson_files,
    insert_tmas_to_db,
    is_airac_current,
    read_coords,
)
from coord_buffer.utils import logger


def parse_args():
    parser = argparse.ArgumentParser(description="Fetch and process TMA data")
    parser.add_argument(
        "input_file",
        nargs="?",
        default=None,
        help="Path to a GeoJSON file with coordinates",
    )
    parser.add_argument(
        "--buffer", type=float, default=0, help="Buffer size in NM (default: 0)"
    )
    parser.add_argument(
        "--check-airac",
        type=str,
        help="Check if the provided AIRAC date (YYYY-MM-DD) is the latest in the database",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.check_airac:
        try:
            is_current = is_airac_current(DB_PARAMS, args.check_airac)
            if is_current:
                logger.info(
                    f"AIRAC date {args.check_airac} is current or newer than the latest in the database"
                )
            else:
                logger.warning(
                    f"AIRAC date {args.check_airac} is older than the latest in the database"
                )
            sys.exit(0 if is_current else 1)
        except Exception as e:
            logger.error(f"Error checking AIRAC date: {e}")
            sys.exit(1)

    if not os.path.exists(OUTPUT_FOLDER):
        logger.info(f"Creating {OUTPUT_FOLDER} folder")
        os.makedirs(OUTPUT_FOLDER)

    # If no input is provided, fetch TMAs & save to DB
    if args.input_file is None:
        logger.info("No input file provided, fetching TMAs")
        try:
            tmas = fetch_tmas()
            gdf = gpd.read_file(BytesIO(tmas))
            gdf = to_wgs84(gdf)
            create_geojson_files(gdf, OUTPUT_FOLDER)
            insert_tmas_to_db(gdf, DB_PARAMS)
            logger.info(f"TMAs saved to {OUTPUT_FOLDER} & inserted into database")
        except Exception as e:
            logger.info(f"Error fetching or processing TMA data: {e}")
            sys.exit(1)
        return

    # Check if coord file exists
    if not os.path.isfile(args.input_file):
        logger.info(f"Input file does not exist: {args.input_file}")
        sys.exit(1)
    logger.info(f"Processing input file: {args.input_file}")
    try:
        coords = read_coords(args.input_file)
        buffered_gdf = buffer_polygon(coords, args.buffer)
        coords_df = buffered_gdf.get_coordinates()
        for _, row in coords_df.iterrows():
            print(to_dms_coords([row["y"], row["x"]]))
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
