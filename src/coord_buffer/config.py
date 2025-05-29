import os

from dotenv import load_dotenv

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
