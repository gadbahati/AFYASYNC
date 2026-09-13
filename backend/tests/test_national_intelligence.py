from app.reports.national_intelligence import _severity, _trend
from app.reports.national_intelligence_schemas import NationalIntelligenceAlert


def test_intelligence_severity_bands_are_ordered():
    assert _severity(0) == "LOW"
    assert _severity(19) == "LOW"
    assert _severity(20) == "MEDIUM"
    assert _severity(44) == "MEDIUM"
    assert _severity(45) == "HIGH"
    assert _severity(69) == "HIGH"
    assert _severity(70) == "CRITICAL"


def test_national_intelligence_alert_schema_restricts_severity_and_category():
    alert = NationalIntelligenceAlert(code="LOW_STOCK", severity="HIGH", category="SUPPLY", title="Low stock", summary="Inventory requires review.", value=4, unit="items", recommendation="Review replenishment.")
    assert alert.severity == "HIGH"
    assert alert.category == "SUPPLY"


def test_intelligence_trend_calculates_change_and_direction():
    trend = _trend("encounters", "Encounters", 120, 100)
    assert trend.change_percent == 20.0
    assert trend.direction == "UP"


def test_intelligence_trend_handles_zero_baseline_as_new_activity():
    trend = _trend("claims", "Claims", 4, 0)
    assert trend.change_percent is None
    assert trend.direction == "UP"
    assert "new in the current period" in trend.interpretation


def test_intelligence_trend_handles_zero_activity_as_flat():
    trend = _trend("claims", "Claims", 0, 0)
    assert trend.change_percent is None
    assert trend.direction == "FLAT"


def test_intelligence_trend_is_flat_for_small_change():
    trend = _trend("claims", "Claims", 100.5, 100)
    assert trend.direction == "FLAT"
    assert trend.change_percent == 0.5
