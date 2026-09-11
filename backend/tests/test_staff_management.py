from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.rbac import service as staff_service


def test_create_staff_requires_facility() -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="FACILITY_CONTEXT_REQUIRED"):
        staff_service.create_staff(db, {"facility_id": None, "person_id": uuid4(), "employee_number": "E1"})


def test_list_staff_is_facility_scoped() -> None:
    db = MagicMock()
    db.scalar.return_value = 0
    db.scalars.return_value = []
    facility_id = uuid4()
    other = uuid4()

    items, total = staff_service.list_staff(db, facility_id)
    assert items == []
    assert total == 0

    count_stmt = db.scalar.call_args[0][0]
    compiled = str(count_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert facility_id.hex in compiled
    assert other.hex not in compiled


def test_update_staff_status_rejects_cross_facility() -> None:
    db = MagicMock()
    staff = SimpleNamespace(id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.get.return_value = staff

    with pytest.raises(ValueError, match="STAFF_NOT_FOUND"):
        staff_service.update_staff_status(db, staff.id, uuid4(), "INACTIVE")

    db.commit.assert_not_called()


def test_assign_staff_role_rejects_inactive_staff() -> None:
    db = MagicMock()
    staff = SimpleNamespace(id=uuid4(), facility_id=uuid4(), status="INACTIVE")
    db.get.side_effect = lambda model, key: staff if model.__name__ == "Staff" else None

    with pytest.raises(ValueError, match="STAFF_NOT_ACTIVE"):
        staff_service.assign_staff_role(db, staff.id, uuid4(), staff.facility_id)

    db.commit.assert_not_called()


def test_assign_staff_role_rejects_missing_role() -> None:
    db = MagicMock()
    facility_id = uuid4()
    staff = SimpleNamespace(id=uuid4(), facility_id=facility_id, status="ACTIVE")

    def _get(model, key):
        if getattr(model, "__name__", "") == "Staff":
            return staff
        return None  # Role missing

    db.get.side_effect = _get

    with pytest.raises(ValueError, match="ROLE_NOT_FOUND"):
        staff_service.assign_staff_role(db, staff.id, uuid4(), facility_id)

    db.commit.assert_not_called()
