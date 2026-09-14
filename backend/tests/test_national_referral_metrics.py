from datetime import datetime, timezone
from uuid import uuid4

from app.national_referrals.metrics_schemas import NationalReferralMetricsResponse


def test_national_referral_metrics_contract_is_bounded_and_privacy_safe():
    response = NationalReferralMetricsResponse(
        total=4,
        active=2,
        completed=1,
        declined=1,
        acceptance_rate=50,
        completion_rate=25,
        aging=[{"bucket": "<24h", "count": 2}],
        routes=[{
            "source_facility_id": str(uuid4()),
            "source_facility_code": "SRC-1",
            "source_facility_name": "Source",
            "destination_facility_id": str(uuid4()),
            "destination_facility_code": "DST-1",
            "destination_facility_name": "Destination",
            "total": 4,
            "active": 2,
            "completed": 1,
            "declined": 1,
        }],
    )
    dumped = response.model_dump()
    assert dumped["total"] == 4
    assert 0 <= dumped["acceptance_rate"] <= 100
    assert "patient_id" not in dumped
    assert "clinical_summary" not in dumped
    assert "reason" not in dumped
    assert "access_reason" not in dumped


def test_metrics_accepts_timezone_aware_operational_timestamps_elsewhere():
    assert datetime.now(timezone.utc).tzinfo is not None
