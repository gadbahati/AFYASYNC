from app.reports.national_intelligence_schemas import NationalIntelligenceResponse


def test_national_intelligence_defaults_to_bounded_signal_page():
    response = NationalIntelligenceResponse(
        start_date="2026-01-01",
        end_date="2026-01-01",
        comparison_start_date="2025-12-31",
        comparison_end_date="2025-12-31",
    )
    assert response.facility_signals == []
    assert response.facility_signals_page == 1
    assert response.facility_signals_page_size == 100
    assert response.facility_signals_total == 0
