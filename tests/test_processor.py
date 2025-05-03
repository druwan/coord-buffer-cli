import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import geopandas as gpd
import psycopg
import pytest
from shapely.geometry import Polygon

from coord_buffer.coords import to_wgs84
from coord_buffer.processor import (
    buffer_polygon,
    create_geojson_files,
    get_latest_airac_date,
    insert_tmas_to_db,
    is_airac_current,
    read_coords,
)


@pytest.fixture
def mock_geodataframe():
    """Fixture for a mock GeoDataFrame."""
    gdf = gpd.GeoDataFrame(
        {
            "NAMEOFAREA": ["Test Area"],
            "TYPEOFAREA": ["TMAS"],
            "POSITIONINDICATOR": ["TEST"],
            "WEF": ["2025-05-15"],
            "DATETIMEOFCHG": [None],
            "NAMEOFOPERATOR": [None],
            "ORIGIN": ["AIP"],
            "LOCATION": ["Test Location"],
            "UPPER": ["FL 95"],
            "LOWER": ["4500"],
            "COMMENT_1": ["C"],
            "COMMENT_2": [None],
            "QUALITY": ["ROUTINE"],
            "CRC_ID": [None],
            "CRC_POS": [None],
            "CRC_TOT": [None],
            "MSID": [4194],
            "IDNR": [21636],
            "MI_STYLE": [None],
            "geometry": [Polygon([(0, 0), (1, 1), (1, 0), (0, 0)])],
        },
        crs="EPSG:4326",
    )
    return gdf


def test_to_wgs84(mock_geodataframe):
    """Test conversion to WGS84 CRS."""
    with patch.object(mock_geodataframe, "to_crs") as mock_to_crs:
        mock_to_crs.return_value = mock_geodataframe
        result = to_wgs84(mock_geodataframe)
        mock_to_crs.assert_called_once_with(epsg=4326)
        assert result is mock_geodataframe


def test_create_geojson_files(tmp_path, mock_geodataframe):
    """Test creating GeoJSON files."""
    folder = tmp_path / "output"
    with (
        patch("coord_buffer.processor.clean_file_name", return_value="TEST_AREA"),
        patch("coord_buffer.processor.os.makedirs") as mock_makedirs,
        patch.object(gpd.GeoDataFrame, "to_file") as mock_to_file,
    ):
        create_geojson_files(mock_geodataframe, str(folder))
        mock_makedirs.assert_called_once_with(str(folder))
        mock_to_file.assert_called_once_with(
            str(folder / "TEST_AREA.geojson"), driver="GeoJSON"
        )


def test_create_geojson_files_skips_tma(mock_geodataframe):
    """Test skipping TMA_ prefixed areas."""
    mock_geodataframe["NAMEOFAREA"] = ["TMA_Skip"]
    with (
        patch("coord_buffer.processor.clean_file_name", return_value="TMA_SKIP"),
        patch("coord_buffer.processor.os.makedirs"),
        patch.object(gpd.GeoDataFrame, "to_file") as mock_to_file,
    ):
        create_geojson_files(mock_geodataframe, "output")
        mock_to_file.assert_not_called()


def test_insert_tmas_to_db(mock_geodataframe):
    """Test inserting TMAs into database."""
    conn_params = {
        "dbname": "test",
        "user": "test",
        "password": "test",
        "host": "localhost",
        "port": "5432",
    }
    with patch("coord_buffer.processor.psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        insert_tmas_to_db(mock_geodataframe, conn_params)

        mock_connect.assert_called_once_with(**conn_params)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


def test_insert_tmas_to_db_skips_tma(mock_geodataframe):
    """Test skipping TMA_ prefixed areas."""
    mock_geodataframe["NAMEOFAREA"] = ["TMA_Skip"]
    conn_params = {
        "dbname": "test",
        "user": "test",
        "password": "test",
        "host": "localhost",
        "port": "5432",
    }
    with patch("coord_buffer.processor.psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        insert_tmas_to_db(mock_geodataframe, conn_params)

        mock_cursor.execute.assert_not_called()


def test_insert_tmas_to_db_connection_error(mock_geodataframe):
    """Test handling database connection error."""
    conn_params = {
        "dbname": "test",
        "user": "test",
        "password": "test",
        "host": "localhost",
        "port": "5432",
    }
    with patch(
        "coord_buffer.processor.psycopg.connect",
        side_effect=psycopg.Error("Connection failed"),
    ):
        with pytest.raises(RuntimeError, match="Failed to insert TMAs into database"):
            insert_tmas_to_db(mock_geodataframe, conn_params)


def test_buffer_polygon():
    """Test buffering a polygon."""
    coords = [[0, 0], [1, 1], [1, 0], [0, 0]]
    gdf = gpd.GeoDataFrame(geometry=[Polygon(coords)], crs="EPSG:4326")
    with (
        patch("geopandas.GeoDataFrame.to_crs") as mock_gdf_to_crs,
        patch("geopandas.GeoSeries.to_crs") as mock_gs_to_crs,
        patch.object(gpd.GeoDataFrame, "buffer") as mock_buffer,
    ):
        mock_gdf_to_crs.return_value = gdf
        mock_gs_to_crs.return_value = gdf.geometry
        mock_buffer.return_value = gdf.geometry
        result = buffer_polygon(coords, 5)
        mock_gdf_to_crs.assert_called_once_with(epsg=3006)
        mock_gs_to_crs.assert_called_once_with(epsg=4326)
        mock_buffer.assert_called_once_with(
            distance=5 * 1852, single_sided=True, join_style=2
        )
        assert isinstance(result, gpd.GeoSeries)


def test_read_coords_valid(tmp_path):
    """Test reading valid GeoJSON coordinates."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 0]]],
                },
            }
        ],
    }
    file = tmp_path / "test.geojson"
    file.write_text(json.dumps(geojson))
    coords = read_coords(file)
    assert coords == [[0, 0], [1, 1], [1, 0], [0, 0]]


def test_read_coords_no_features(tmp_path):
    """Test GeoJSON with no features."""
    geojson = {"type": "FeatureCollection", "features": []}
    file = tmp_path / "empty.geojson"
    file.write_text(json.dumps(geojson))
    with pytest.raises(ValueError, match="GeoJSON file has no features"):
        read_coords(file)


def test_read_coords_invalid_geometry(tmp_path):
    """Test GeoJSON with invalid geometry type."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}}
        ],
    }
    file = tmp_path / "invalid.geojson"
    file.write_text(json.dumps(geojson))
    with pytest.raises(ValueError, match="Unsupported geometry type: Point"):
        read_coords(file)


def test_read_coords_invalid_coords(tmp_path):
    """Test GeoJSON with invalid coordinate format."""
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1], [1, 0], [0, 0]]],
                },
            }
        ],
    }
    file = tmp_path / "invalid_coords.geojson"
    file.write_text(json.dumps(geojson))
    with pytest.raises(ValueError, match="Invalid coordinate format:"):
        read_coords(file)


def test_get_latest_airac_date():
    """Test retrieving the latest AIRAC date."""
    conn_params = {
        "dbname": "test",
        "user": "test",
        "password": "test",
        "host": "localhost",
        "port": "5432",
    }
    with patch("coord_buffer.processor.psycopg.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = [datetime(2025, 5, 15).date()]

        latest_wef = get_latest_airac_date(conn_params)
        mock_cursor.execute.assert_called_once_with("SELECT MAX(wef) FROM tmas")
        assert latest_wef == datetime(2025, 5, 15).date()


def test_is_airac_current():
    """Test checking if an AIRAC date is current."""
    conn_params = {
        "dbname": "test",
        "user": "test",
        "password": "test",
        "host": "localhost",
        "port": "5432",
    }
    with patch(
        "coord_buffer.processor.get_latest_airac_date",
        return_value=datetime(2025, 5, 15).date(),
    ):
        assert is_airac_current(conn_params, "2025-05-15") is True
        assert is_airac_current(conn_params, "2025-06-12") is True
        assert is_airac_current(conn_params, "2025-04-17") is False
        with pytest.raises(ValueError, match="Invalid AIRAC date format"):
            is_airac_current(conn_params, "invalid")
