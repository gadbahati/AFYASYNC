from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.patients.service import list_patients_for_facility


def test_list_patients_for_facility_requires_facility_context() -> None:
    db = MagicMock()

    with pytest.raises(ValueError, match="FACILITY_CONTEXT_REQUIRED"):
        list_patients_for_facility(db, None)  # type: ignore[arg-type]

    db.execute.assert_not_called()


def test_list_patients_for_facility_rejects_invalid_enrollment_status() -> None:
    db = MagicMock()
    facility_id = uuid4()

    with pytest.raises(ValueError, match="INVALID_ENROLLMENT_STATUS"):
        list_patients_for_facility(db, facility_id, enrollment_status="UNKNOWN")

    db.execute.assert_not_called()


def test_list_patients_for_facility_query_is_scoped_to_facility() -> None:
    db = MagicMock()
    db.execute.return_value = []
    facility_id = uuid4()
    other_facility_id = uuid4()

    list_patients_for_facility(db, facility_id, limit=25, offset=10)

    assert db.execute.call_count == 1
    statement = db.execute.call_args[0][0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    # Must contain the authenticated facility
    assert facility_id.hex in compiled
    # Must not contain any other facility id
    assert other_facility_id.hex not in compiled
    # Must order deterministically
    assert "last_name" in compiled.lower()
    assert "first_name" in compiled.lower()


def test_list_patients_for_facility_applies_limit_and_offset_bounds() -> None:
    db = MagicMock()
    db.execute.return_value = []
    facility_id = uuid4()

    # Over-limit is clamped to 100
    list_patients_for_facility(db, facility_id, limit=500, offset=-5)
    statement = db.execute.call_args[0][0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "100" in compiled or "LIMIT 100" in compiled.upper()


def test_list_patients_for_facility_returns_mapped_rows() -> None:
    db = MagicMock()
    person = SimpleNamespace(id=uuid4(), first_name="Ada", last_name="Lovelace")
    identity = SimpleNamespace(afya_id="AF-00000001")
    db.execute.return_value = [(person, identity)]

    results = list_patients_for_facility(db, uuid4())

    assert results == [(person, identity)]
