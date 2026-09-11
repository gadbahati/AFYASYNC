from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.clinical.service import get_encounter_clinical_summary
from app.encounters.service import list_patient_encounters_for_facility


def test_list_patient_encounters_requires_enrollment() -> None:
    db = MagicMock()
    db.scalar.return_value = None  # no PatientFacility membership

    with pytest.raises(ValueError, match="PATIENT_NOT_IN_FACILITY"):
        list_patient_encounters_for_facility(db, uuid4(), uuid4())

    db.execute.assert_not_called()


def test_list_patient_encounters_scopes_to_facility() -> None:
    db = MagicMock()
    facility_id = uuid4()
    other_facility = uuid4()
    patient_id = uuid4()
    db.scalar.side_effect = [uuid4(), 0]  # membership id, then count
    db.scalars.return_value = []

    items, total = list_patient_encounters_for_facility(db, patient_id, facility_id)
    assert items == []
    assert total == 0

    # count query should be facility-scoped
    count_stmt = db.scalar.call_args_list[1][0][0]
    compiled = str(count_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert facility_id.hex in compiled
    assert other_facility.hex not in compiled


def test_clinical_summary_rejects_cross_facility() -> None:
    db = MagicMock()
    encounter = SimpleNamespace(id=uuid4(), facility_id=uuid4())
    db.get.return_value = encounter

    with pytest.raises(ValueError, match="FACILITY_ACCESS_DENIED"):
        get_encounter_clinical_summary(db, encounter.id, uuid4())


def test_clinical_summary_rejects_missing_encounter() -> None:
    db = MagicMock()
    db.get.return_value = None

    with pytest.raises(ValueError, match="ENCOUNTER_NOT_FOUND"):
        get_encounter_clinical_summary(db, uuid4(), uuid4())
