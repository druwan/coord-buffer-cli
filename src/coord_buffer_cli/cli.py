import argparse

from coord_buffer_cli.utils import (
    buffer_polygon,
    list_coords_from_db,
    logger,
    read_coords,
    read_coords_from_db,
    to_dms_coords,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Creates a specified buffer around user specified area."
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="Prints list of available geometries and their id.",
    )
    parser.add_argument(
        "--msid",
        default=None,
        help="Get coords for the selected geometries.",
    )
    parser.add_argument(
        "-f",
        "--input_file",
        default=None,
        help="Path to a GeoJSON file with coordinates",
    )
    parser.add_argument(
        "-b", "--buffer", type=float, default=0, help="Buffer size in NM (default: 0)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        if args.list:
            list_coords_from_db()
            return
        elif args.msid:
            logger.info(f"Processing msid: {args.msid}")
            coords = read_coords_from_db(args.msid)
        elif args.input_file:
            logger.info(f"Processing input file: {args.input_file}")
            coords = read_coords(args.input_file)
        buffered_gdf = buffer_polygon(coords, args.buffer)
        coords_df = buffered_gdf.get_coordinates()
        for _, row in coords_df.iterrows():
            print(to_dms_coords([row["y"], row["x"]]))
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return


if __name__ == "__main__":
    main()
