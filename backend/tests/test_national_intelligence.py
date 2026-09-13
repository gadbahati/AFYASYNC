from app.reports.national_intelligence import _severity
from app.reports.national_intelligence_schemas import NationalIntelligenceAlert


def test_intelligence_severity_bands_are_ordered():
    assert _severity(0) == "LOW"
    assert _severity(20) == "MEDIUM"
    assert _severity(45) == "HIGH"
    assert _severity(70) == "CRITICAL"


def test_national_intelligence_alert_schema_restricts_severity_and_category():
    alert = NationalIntelligenceAlert(
        code="LOW_STOCK",
        severity="HIGH",
        category="SUPPLY",
        title="Low stock",
        summary="Inventory requires review.",
        value=4,
        unit="items",
        recommendation="Review replenishment.",
    )
    assert alert.severity == "HIGH"
    assert alert.category == "SUPPLY"
