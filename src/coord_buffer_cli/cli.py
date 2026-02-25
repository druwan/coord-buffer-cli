from coord_buffer_cli.config import logger, parse_args
from coord_buffer_cli.utils import (
    buffer_polygon,
    console,
    list_coords_from_db,
    print_coordinates,
    read_coords,
    read_coords_from_db,
)


def main():
    args = parse_args()

    try:
        if args.list:
            list_coords_from_db()
            return

        if args.msid:
            logger.info(f"Processing MSID: {args.msid}")
            coords, nameofarea = read_coords_from_db(args.msid)
        else:
            logger.info(f"Processing file: {args.input_file}")
            coords, nameofarea = read_coords(args.input_file)

        buffered_gdf = buffer_polygon(coords, args.buffer)
        coords_df = buffered_gdf.get_coordinates()

        console.print(
            f"\n[bold green]{nameofarea} Buffered • {args.buffer} NM[/bold green]\n"
        )
        print_coordinates(coords_df)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return


if __name__ == "__main__":
    main()
