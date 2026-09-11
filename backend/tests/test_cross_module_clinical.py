from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from app.clinical.service import get_encounter_clinical_summary


def test_clinical_summary_includes_lab_and_pharmacy() -> None:
    facility_id = uuid4()
    encounter_id = uuid4()
    encounter = SimpleNamespace(id=encounter_id, facility_id=facility_id, patient_id=uuid4())

    db = MagicMock()
    db.get.return_value = encounter

    # scalars() is called for vitals, diagnoses, lab_orders, prescriptions
    empty = []
    db.scalars.side_effect = [empty, empty, empty, empty]
    db.scalar.return_value = None  # consultation

    summary = get_encounter_clinical_summary(db, encounter_id, facility_id)

    assert summary["encounter"] is encounter
    assert "lab_orders" in summary
    assert "prescriptions" in summary
    assert summary["lab_orders"] == []
    assert summary["prescriptions"] == []
    assert summary["vitals"] == []
    assert summary["diagnoses"] == []
    assert summary["consultation"] is None
