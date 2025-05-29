from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest

from coord_buffer.cli import main


@pytest.fixture
def mock_args():
    """Fixture to create a mock args object."""
    args = MagicMock()
    args.input_file = None
    args.buffer = 0
    args.msid = None
    args.list = False
    return args


@pytest.fixture
def mock_geodataframe():
    """Fixture to create a mock GeoDataFrame."""
    gdf = MagicMock(spec=gpd.GeoDataFrame)
    gdf.to_crs.return_value = gdf
    coords_df = pd.DataFrame({"x": [0, 1], "y": [0, 1]})
    gdf.get_coordinates.return_value = coords_df
    return gdf


def test_list_argument_triggers_db_listing(mock_args):
    mock_args.list = True
    with (
        patch("coord_buffer.cli.parse_args", return_value=mock_args),
        patch("coord_buffer.cli.list_coords_from_db") as mock_list,
    ):
        main()
        mock_list.assert_called_once()


def test_msid_argument_triggers_db_read(mock_args, mock_geodataframe):
    mock_args.msid = "123"
    mock_args.buffer = 10
    with (
        patch("coord_buffer.cli.parse_args", return_value=mock_args),
        patch(
            "coord_buffer.cli.read_coords_from_db", return_value=[[0, 0], [1, 1]]
        ) as mock_read_db,
        patch(
            "coord_buffer.cli.buffer_polygon", return_value=mock_geodataframe
        ) as mock_buffer,
        patch("coord_buffer.cli.to_dms_coords") as mock_dms,
    ):
        main()
        mock_read_db.assert_called_once_with("123")
        mock_buffer.assert_called_once()
        mock_dms.assert_called()


def test_input_file_argument_triggers_file_read(mock_args, mock_geodataframe):
    mock_args.input_file = "test.geojson"
    mock_args.buffer = 5
    with (
        patch("coord_buffer.cli.parse_args", return_value=mock_args),
        patch(
            "coord_buffer.cli.read_coords", return_value=[[0, 0], [1, 1]]
        ) as mock_read_file,
        patch(
            "coord_buffer.cli.buffer_polygon", return_value=mock_geodataframe
        ) as mock_buffer,
        patch("coord_buffer.cli.to_dms_coords") as mock_dms,
    ):
        main()
        mock_read_file.assert_called_once_with("test.geojson")
        mock_buffer.assert_called_once_with([[0, 0], [1, 1]], 5)
        mock_dms.assert_called()


def test_exception_handling_logs_error(mock_args):
    mock_args.input_file = "test.geojson"
    with (
        patch("coord_buffer.cli.parse_args", return_value=mock_args),
        patch("coord_buffer.cli.read_coords", side_effect=Exception("Boom!")),
        patch("coord_buffer.cli.logger.error") as mock_log,
    ):
        main()
        mock_log.assert_called_once()
        assert "Boom!" in str(mock_log.call_args[0][0])
