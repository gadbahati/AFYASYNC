from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.facilities import service as facility_service


def test_update_facility_requires_existing_facility() -> None:
    db = MagicMock()
    db.get.return_value = None
    with pytest.raises(ValueError, match="FACILITY_NOT_FOUND"):
        facility_service.update_facility(db, uuid4(), {"name": "New Name"})
    db.commit.assert_not_called()


def test_update_facility_status_rejects_invalid_status() -> None:
    db = MagicMock()
    with pytest.raises(ValueError, match="INVALID_FACILITY_STATUS"):
        facility_service.update_facility_status(db, uuid4(), "UNKNOWN")
    db.commit.assert_not_called()


def test_update_department_status_rejects_cross_facility() -> None:
    db = MagicMock()
    department = SimpleNamespace(id=uuid4(), facility_id=uuid4(), status="ACTIVE")
    db.get.return_value = department

    with pytest.raises(ValueError, match="DEPARTMENT_NOT_FOUND"):
        facility_service.update_department_status(db, uuid4(), department.id, "INACTIVE")

    db.commit.assert_not_called()


def test_create_department_rejects_duplicate_code() -> None:
    db = MagicMock()
    facility_id = uuid4()
    db.get.return_value = SimpleNamespace(id=facility_id)
    db.scalar.return_value = SimpleNamespace(id=uuid4())  # existing department

    with pytest.raises(ValueError, match="DEPARTMENT_CODE_EXISTS"):
        facility_service.create_department(db, facility_id, {"name": "Lab", "code": "LAB"})

    db.commit.assert_not_called()
