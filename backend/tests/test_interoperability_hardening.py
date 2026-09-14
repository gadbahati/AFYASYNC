from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.interoperability.clinical_schemas import FHIRBundleResource, FHIREncounterResource


def test_fhir_bundle_rejects_more_than_101_entries():
    with pytest.raises(ValueError):
        FHIRBundleResource(total=102)


def test_fhir_encounter_rejects_empty_status():
    with pytest.raises(ValueError):
        FHIREncounterResource(
            id=uuid4(),
            status="",
            class_code="OUTPATIENT",
            period_start=datetime.now(timezone.utc),
            patient_id=uuid4(),
        )
