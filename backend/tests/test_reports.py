from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.reports.service import build_facility_report


def test_facility_report_aggregates_real_facility_scoped_metrics() -> None:
    db = MagicMock()
    db.scalar.side_effect = [12, 7, Decimal("1250.50"), Decimal("900.25")]
    db.execute.side_effect = [
        SimpleNamespace(one=lambda: (Decimal("2000.00"), Decimal("1200.00"), Decimal("800.00"))),
        SimpleNamespace(one=lambda: (4, Decimal("1100.00"), Decimal("950.00"), Decimal("700.00"))),
    ]

    facility_id = uuid4()
    result = build_facility_report(db, facility_id, date(2026, 1, 1), date(2026, 1, 31), actor_user_id=uuid4())

    assert result["facility_id"] == str(facility_id)
    assert result["patients"] == 12
    assert result["encounters"] == 7
    assert result["charges_total"] == Decimal("1250.50")
    assert result["invoices_total"] == Decimal("2000.00")
    assert result["payer_billed"] == Decimal("1200.00")
    assert result["patient_billed"] == Decimal("800.00")
    assert result["confirmed_payments"] == Decimal("900.25")
    assert result["claims"] == 4
    assert result["claims_amount"] == Decimal("1100.00")
    assert result["claims_approved"] == Decimal("950.00")
    assert result["claims_paid"] == Decimal("700.00")
    db.commit.assert_called_once()


def test_facility_report_rejects_reversed_date_range() -> None:
    with pytest.raises(ValueError, match="INVALID_REPORT_DATE_RANGE"):
        build_facility_report(MagicMock(), uuid4(), date(2026, 2, 1), date(2026, 1, 31))
