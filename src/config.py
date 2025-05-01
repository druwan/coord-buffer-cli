import os

from dotenv import load_dotenv

load_dotenv()

# Constants
BUFFER_MULTIPLIER = 1852
DEFAULT_EPSG = 4326
METRIC_EPSG = 3006
TMA_URL = os.getenv("TMA_URL", "https://daim.lfv.se/geoserver/wfs")
OUTPUT_FOLDER = os.getenv("OUTPUT_FOLDER", "POLYGONES")
