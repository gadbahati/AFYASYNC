from datetime import date
from uuid import uuid4

import pytest

from app.coverage.adjudication_schemas import BenefitAdjudicationRequest


def test_benefit_adjudication_request_requires_service_scope():
    with pytest.raises(ValueError):
        BenefitAdjudicationRequest(coverage_id=uuid4(), requested_amount=100)


def test_benefit_adjudication_request_bounds_amount():
    with pytest.raises(ValueError):
        BenefitAdjudicationRequest(coverage_id=uuid4(), service_code="CONSULT", requested_amount=0)
    with pytest.raises(ValueError):
        BenefitAdjudicationRequest(coverage_id=uuid4(), service_code="CONSULT", requested_amount=10_000_001)


def test_benefit_adjudication_request_normal_fields():
    request = BenefitAdjudicationRequest(
        coverage_id=uuid4(),
        service_code="CONSULT",
        requested_amount=250,
    )
    assert request.service_code == "CONSULT"
    assert request.requested_amount == 250
