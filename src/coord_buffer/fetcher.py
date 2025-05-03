import requests
from tenacity import retry, stop_after_attempt, wait_fixed

from coord_buffer.config import DEFAULT_EPSG, TMA_URL


def fetch_tmas(epsg=DEFAULT_EPSG, url=None):
    """Fetch TMAs from WFS service."""
    url = url or TMA_URL
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typename": "mais:TMAS,mais:TMAW",
        "outputFormat": "application/json",
        "srsName": f"EPSG:{epsg}",
    }

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _fetch():
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.content

    return _fetch()
