import pytest

from coord_buffer.coords import dms_to_dd_coords, to_dms_coords


def test_dms_to_dd_coords():
    """Test DMS to decimal degrees conversion."""
    assert abs(dms_to_dd_coords("123456N") - 12.582222222222223) < 1e-10
    assert abs(dms_to_dd_coords("123456S") - (-12.582222222222223)) < 1e-10
    with pytest.raises(ValueError):
        dms_to_dd_coords("invalid")


def test_to_dms_coords():
    """Test decimal degrees to DMS string conversion."""
    assert to_dms_coords([12.582222222222223, 1.0]) == "123456N 0010000E"
    assert to_dms_coords([-12.582222222222223, -1.0]) == "123456S 0010000W"
