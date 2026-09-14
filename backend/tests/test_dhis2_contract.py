import pytest
from app.interoperability.dhis2_service import _month_window

def test_dhis2_period_window_handles_year_boundary():
    start, end = _month_window("202612")
    assert start.year == 2026 and start.month == 12
    assert end.year == 2027 and end.month == 1

def test_dhis2_period_rejects_invalid_month():
    with pytest.raises(ValueError, match="INVALID_DHIS2_PERIOD"):
        _month_window("202613")
