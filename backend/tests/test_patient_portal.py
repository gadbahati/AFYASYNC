from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.portal.service import PortalError, get_my_encounter, require_patient_person_id


def test_require_patient_person_id_rejects_missing_identity() -> None:
    with pytest.raises(PortalError, match="PATIENT_IDENTITY_REQUIRED"):
        require_patient_person_id(None)


def test_get_my_encounter_rejects_other_patients_record() -> None:
    db = MagicMock()
    owner = uuid4()
    other = uuid4()
    encounter = SimpleNamespace(id=uuid4(), patient_id=other)
    db.get.return_value = encounter

    with pytest.raises(PortalError, match="ENCOUNTER_NOT_FOUND"):
        get_my_encounter(db, owner, encounter.id)
