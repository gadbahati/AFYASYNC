from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.coverage.service import create_benefit_rule, create_coverage


def test_create_coverage_audits_before_commit() -> None:
    payer_id = uuid4()
    person_id = uuid4()
    coverage_id = uuid4()
    payer = MagicMock(status="ACTIVE")
    db = MagicMock()
    db.get.return_value = payer
    coverage = MagicMock(id=coverage_id, payer_id=payer_id, person_id=person_id, payer_plan_id=None)
    with patch("app.coverage.service.Coverage", return_value=coverage), patch("app.coverage.service.record_audit") as audit:
        payload = MagicMock(
            start_date=None,
            end_date=None,
            payer_id=payer_id,
            payer_plan_id=None,
        )
        payload.model_dump.return_value = {"person_id": person_id, "payer_id": payer_id, "payer_plan_id": None}
        create_coverage(db, payload, actor_user_id=uuid4())

    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    assert db.method_calls.index(next(call for call in db.method_calls if call[0] == "commit")) > db.method_calls.index(next(call for call in db.method_calls if call[0] == "flush"))


def test_create_benefit_rule_audits_before_commit() -> None:
    payer_id = uuid4()
    rule_id = uuid4()
    payer = MagicMock(status="ACTIVE")
    db = MagicMock()
    db.get.return_value = payer
    rule = MagicMock(id=rule_id, payer_id=payer_id, payer_plan_id=None, service_code="CBC", service_type="LAB")
    with patch("app.coverage.service.PayerBenefitRule", return_value=rule), patch("app.coverage.service.record_audit") as audit:
        payload = MagicMock(effective_from=None, effective_to=None, payer_id=payer_id, payer_plan_id=None)
        payload.model_dump.return_value = {"payer_id": payer_id, "payer_plan_id": None, "service_code": "CBC", "service_type": "LAB"}
        create_benefit_rule(db, payload, actor_user_id=uuid4())

    audit.assert_called_once()
    assert audit.call_args.kwargs["commit"] is False
    flush_index = next(i for i, call in enumerate(db.method_calls) if call[0] == "flush")
    commit_index = next(i for i, call in enumerate(db.method_calls) if call[0] == "commit")
    assert flush_index < commit_index
