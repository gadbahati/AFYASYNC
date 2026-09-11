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
    db.scalar.assert_not_called()


def test_list_patients_for_facility_rejects_invalid_enrollment_status() -> None:
    db = MagicMock()
    facility_id = uuid4()

    with pytest.raises(ValueError, match="INVALID_ENROLLMENT_STATUS"):
        list_patients_for_facility(db, facility_id, enrollment_status="UNKNOWN")

    db.execute.assert_not_called()
    db.scalar.assert_not_called()


def test_list_patients_for_facility_query_is_scoped_to_facility() -> None:
    db = MagicMock()
    db.scalar.return_value = 0
    db.execute.return_value.all.return_value = []
    facility_id = uuid4()
    other_facility_id = uuid4()

    items, total = list_patients_for_facility(db, facility_id, limit=25, offset=10)

    assert items == []
    assert total == 0
    assert db.scalar.call_count == 1
    assert db.execute.call_count == 1

    count_stmt = db.scalar.call_args[0][0]
    compiled_count = str(count_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert facility_id.hex in compiled_count
    assert other_facility_id.hex not in compiled_count

    statement = db.execute.call_args[0][0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert facility_id.hex in compiled
    assert other_facility_id.hex not in compiled
    assert "last_name" in compiled.lower()
    assert "first_name" in compiled.lower()


def test_list_patients_for_facility_applies_limit_and_offset_bounds() -> None:
    db = MagicMock()
    db.scalar.return_value = 0
    db.execute.return_value.all.return_value = []
    facility_id = uuid4()

    list_patients_for_facility(db, facility_id, limit=500, offset=-5)
    statement = db.execute.call_args[0][0]
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))
    assert "100" in compiled or "LIMIT 100" in compiled.upper()


def test_list_patients_for_facility_returns_mapped_rows_and_total() -> None:
    db = MagicMock()
    person = SimpleNamespace(id=uuid4(), first_name="Ada", last_name="Lovelace")
    identity = SimpleNamespace(afya_id="AF-00000001")
    db.scalar.return_value = 1
    db.execute.return_value.all.return_value = [(person, identity)]

    items, total = list_patients_for_facility(db, uuid4())

    assert items == [(person, identity)]
    assert total == 1
