from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.billing.service import BillingError, create_invoice
from app.coverage.service import calculate_charge_responsibility


def test_payer_percentage_and_copay_are_applied() -> None:
    coverage = SimpleNamespace(payer_id=uuid4(), payer_plan_id=uuid4())
    rule = SimpleNamespace(
        id=uuid4(),
        payer_plan_id=coverage.payer_plan_id,
        service_code="CONSULT",
        service_type="CONSULTATION",
        payer_percent=Decimal("80"),
        fixed_patient_copay=Decimal("50"),
        max_covered_amount=None,
    )
    with patch("app.coverage.service.find_benefit_rule", return_value=rule):
        payer, patient, rule_id = calculate_charge_responsibility(
            MagicMock(), coverage, amount=Decimal("500"), service_code="CONSULT", service_type="CONSULTATION"
        )
    assert payer == Decimal("400.00")
    assert patient == Decimal("100.00")
    assert rule_id == rule.id


def test_max_covered_amount_limits_payer_share() -> None:
    coverage = SimpleNamespace(payer_id=uuid4(), payer_plan_id=None)
    rule = SimpleNamespace(
        id=uuid4(), payer_plan_id=None, service_code=None, service_type="LAB",
        payer_percent=Decimal("100"), fixed_patient_copay=Decimal("0"), max_covered_amount=Decimal("300"),
    )
    with patch("app.coverage.service.find_benefit_rule", return_value=rule):
        payer, patient, _ = calculate_charge_responsibility(
            MagicMock(), coverage, amount=Decimal("500"), service_code="CBC", service_type="LAB"
        )
    assert payer == Decimal("300.00")
    assert patient == Decimal("200.00")


def test_missing_rule_is_never_silently_treated_as_full_coverage() -> None:
    coverage = SimpleNamespace(payer_id=uuid4(), payer_plan_id=None)
    with patch("app.coverage.service.find_benefit_rule", return_value=None):
        with pytest.raises(ValueError, match="COVERAGE_RULE_NOT_CONFIGURED"):
            calculate_charge_responsibility(
                MagicMock(), coverage, amount=Decimal("100"), service_code="XRAY", service_type="IMAGING"
            )


def test_invoice_without_coverage_assigns_full_patient_responsibility() -> None:
    facility_id = uuid4()
    encounter = SimpleNamespace(id=uuid4(), facility_id=facility_id, patient_id=uuid4())
    charge = SimpleNamespace(id=uuid4(), total_amount=Decimal("150.00"), quantity=1, unit_price=Decimal("150.00"), service_id=uuid4(), created_at=None)
    service = SimpleNamespace(id=charge.service_id, facility_id=facility_id, code="CONSULT", name="Consultation", service_type="CONSULTATION", price=Decimal("150.00"))
    db = MagicMock()
    db.get.side_effect = [encounter, service]
    db.scalar.side_effect = [None, False]
    db.scalars.return_value = [charge]
    db.add = MagicMock()
    db.flush = MagicMock()
    db.commit = MagicMock()
    db.refresh = MagicMock()

    with patch("app.billing.service.record_audit"), patch("app.billing.service.get_verified_current_coverage", return_value=None), patch("app.billing.service.has_current_unverified_coverage", return_value=False), patch("app.billing.service.notify_patient_event"):
        invoice = create_invoice(db, facility_id, encounter.id)

    assert invoice.total_amount == Decimal("150.00")
    assert invoice.payer_amount == Decimal("0")
    assert invoice.patient_amount == Decimal("150.00")
