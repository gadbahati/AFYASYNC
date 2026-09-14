from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.interoperability.clinical_schemas import (
    FHIRBundleEntry,
    FHIRBundleResource,
    FHIREncounterResource,
)
from app.interoperability.schemas import FHIRPatientResource


def test_minimal_clinical_bundle_accepts_patient_and_encounter():
    patient = FHIRPatientResource(id=uuid4(), active=True)
    encounter = FHIREncounterResource(
        id=uuid4(),
        status="FINISHED",
        class_code="OUTPATIENT",
        period_start=datetime.now(timezone.utc),
        patient_id=patient.id,
    )
    bundle = FHIRBundleResource(entry=[
        FHIRBundleEntry(fullUrl=f"urn:uuid:{patient.id}", resource=patient),
        FHIRBundleEntry(fullUrl=f"urn:uuid:{encounter.id}", resource=encounter),
    ], total=2)
    assert bundle.resourceType == "Bundle"
    assert bundle.total == 2
    assert len(bundle.entry) == 2


def test_bundle_rejects_negative_total():
    with pytest.raises(ValidationError):
        FHIRBundleResource(total=-1)


def test_encounter_resource_requires_bounded_status_and_class():
    with pytest.raises(ValidationError):
        FHIREncounterResource(
            id=uuid4(), status="", class_code="OUTPATIENT",
            period_start=datetime.now(timezone.utc), patient_id=uuid4(),
        )
