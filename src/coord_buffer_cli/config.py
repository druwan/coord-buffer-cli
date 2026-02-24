import argparse
import logging
import os

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich_argparse import RichHelpFormatter

load_dotenv()

# Constants
BUFFER_MULTIPLIER = 1852
DEFAULT_EPSG = 4326
METRIC_EPSG = 3006
DB_PARAMS = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": os.getenv("POSTGRES_HOST"),
    "port": os.getenv("5432"),
}


logging.basicConfig(level="DEBUG", format="%(message)s", handlers=[RichHandler()])
logger = logging.getLogger(__name__)

console = Console()


class CustomFormatter(RichHelpFormatter):
    styles = {
        "argparse.prog": "bold cyan",
        "argparse.args": "cyan",
        "argparse.metavar": "yellow",
        "argparse.help": "white",
    }


def parse_args():
    parser = argparse.ArgumentParser(
        prog="coord_buffer_cli",
        description="Creates a specified buffer around user specified area.",
        epilog="Ex: uv run coord_buffer_cli --msid 3982 -b 5",
        formatter_class=CustomFormatter,
    )
    source_group = parser.add_mutually_exclusive_group(required=True)

    source_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="Prints list of available geometries and their id.",
    )

    source_group.add_argument(
        "--msid",
        type=int,
        help="Fetch coordinates for the given MSID.",
    )

    source_group.add_argument(
        "-f",
        "--input_file",
        help="Path to a GeoJSON file.",
    )
    parser.add_argument(
        "-b", "--buffer", type=float, default=0.0, help="Buffer size in nautical miles."
    )
    return parser.parse_args()
