from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest

from src.cli import main


@pytest.fixture
def mock_args():
    """Fixture to create a mock args object."""
    args = MagicMock()
    args.input_file = None
    args.buffer = 0
    return args


@pytest.fixture
def mock_geodataframe():
    """Fixture to create a mock GeoDataFrame."""
    gdf = MagicMock(spec=gpd.GeoDataFrame)
    gdf.to_crs.return_value = gdf
    coords_df = pd.DataFrame({"x": [0, 1], "y": [0, 1]})
    gdf.get_coordinates.return_value = coords_df
    return gdf


def test_no_arguments_fetches_tmas(mock_args, mock_geodataframe):
    """Test that no arguments triggers TMA fetching."""
    with (
        patch("src.cli.parse_args", return_value=mock_args),
        patch("src.cli.fetch_tmas", return_value=b"{}") as mock_fetch,
        patch("src.cli.gpd.read_file", return_value=mock_geodataframe) as mock_read,
        patch("src.cli.to_wgs84", return_value=mock_geodataframe) as mock_to_wgs84,
        patch("src.cli.create_geojson_files") as mock_create,
    ):
        main()
        mock_fetch.assert_called_once()
        mock_read.assert_called_once()
        mock_to_wgs84.assert_called_once()
        mock_create.assert_called_once()


def test_file_not_exists(mock_args):
    """Test that a non-existent input file raises SystemExit."""
    mock_args.input_file = "nonexistent.geojson"
    with (
        patch("src.cli.parse_args", return_value=mock_args),
        patch("src.cli.os.path.isfile", return_value=False),
    ):
        with pytest.raises(SystemExit):
            main()


def test_valid_file_processing(mock_args, mock_geodataframe):
    """Test processing a valid input file."""
    mock_args.input_file = "valid.geojson"
    mock_args.buffer = 5
    with (
        patch("src.cli.parse_args", return_value=mock_args),
        patch("src.cli.os.path.isfile", return_value=True),
        patch("src.cli.read_coords", return_value=[[0, 0], [1, 1]]) as mock_read,
        patch("src.cli.buffer_polygon", return_value=mock_geodataframe) as mock_buffer,
        patch("src.cli.to_dms_coords") as mock_dms,
    ):
        main()
        mock_read.assert_called_once_with("valid.geojson")
        mock_buffer.assert_called_once_with([[0, 0], [1, 1]], 5)
        mock_dms.assert_called()
        assert mock_dms.call_count == 2  # Called for each coordinate pair


def test_dms_output(mock_args):
    """Test DMS output for known coordinates."""
    mock_args.input_file = "valid.geojson"
    mock_args.buffer = 0
    coords_df = pd.DataFrame({"x": [12.582222222222223], "y": [1.0]})
    gdf = MagicMock(spec=gpd.GeoDataFrame)
    gdf.get_coordinates.return_value = coords_df
    with (
        patch("src.cli.parse_args", return_value=mock_args),
        patch("src.cli.os.path.isfile", return_value=True),
        patch("src.cli.read_coords", return_value=[[0, 0]]) as mock_read,
        patch("src.cli.buffer_polygon", return_value=gdf) as mock_buffer,
        patch("src.cli.to_dms_coords") as mock_dms,
    ):
        main()
        mock_read.assert_called_once_with("valid.geojson")
        mock_buffer.assert_called_once_with([[0, 0]], 0)
        mock_dms.assert_called_with([1.0, 12.582222222222223])  # [y, x] order
