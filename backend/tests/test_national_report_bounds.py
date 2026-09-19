from datetime import date
import pytest

from app.reports.national_service import _window


def test_national_report_rejects_reversed_window():
    with pytest.raises(ValueError, match="INVALID_REPORT_DATE_RANGE"):
        _window(date(2026, 2, 1), date(2026, 1, 1))


def test_national_report_window_is_half_open():
    start, end = _window(date(2026, 1, 1), date(2026, 1, 31))
    assert end > start
    assert (end - start).days == 31
