import re

from coord_buffer.config import DEFAULT_EPSG


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
