from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.encounters.service import create_encounter, get_encounter_for_facility


def test_create_encounter_requires_patient_enrollment(monkeypatch) -> None:
    db = MagicMock()
    patient_id = uuid4()
    facility_id = uuid4()
    department_id = uuid4()

    db.get.side_effect = lambda model, key: SimpleNamespace(
        id=key,
        status="ACTIVE",
        facility_id=facility_id,
    )
    db.scalar.return_value = None  # no PatientFacility membership

    with pytest.raises(ValueError, match="PATIENT_NOT_IN_FACILITY"):
        create_encounter(
            db,
            {
                "patient_id": patient_id,
                "facility_id": facility_id,
                "department_id": department_id,
                "encounter_type": "OPD",
            },
            created_by=uuid4(),
        )

    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_get_encounter_for_facility_rejects_other_facility() -> None:
    db = MagicMock()
    encounter = SimpleNamespace(id=uuid4(), facility_id=uuid4())
    db.get.return_value = encounter

    with pytest.raises(ValueError, match="FACILITY_ACCESS_DENIED"):
        get_encounter_for_facility(db, encounter.id, uuid4())
