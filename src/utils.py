import logging
import re
import unicodedata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def clean_file_name(name):
    name = unicodedata.normalize("NFKD", name)
    name = name.strip()
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = re.sub(r"\s+", "_", name)
    return name.upper()
