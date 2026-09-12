from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi import HTTPException

import app.auth.dependencies as auth_dependencies


def test_get_facility_context_query_requires_active_facility(monkeypatch) -> None:
    db = Mock()
    db.scalar.return_value = None
    user = SimpleNamespace(person_id=uuid4())
    facility_id = uuid4()

    try:
        auth_dependencies.get_facility_context(
            payload={"facility_id": str(facility_id)},
            user=user,
            db=db,
        )
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "FACILITY_ACCESS_DENIED"
    else:
        raise AssertionError("Expected inactive or unauthorized facility access to be denied")

    statement = db.scalar.call_args.args[0]
    compiled = statement.compile()
    assert "facilities.status" in str(compiled)
    assert "ACTIVE" in compiled.params.values()


def test_require_permission_query_requires_active_facility() -> None:
    db = Mock()
    db.scalar.return_value = None
    user = SimpleNamespace(person_id=uuid4())
    facility_id = uuid4()
    dependency = auth_dependencies.require_permission("patients.record.read")

    try:
        dependency(user=user, facility_id=facility_id, db=db)
    except HTTPException as exc:
        assert exc.status_code == 403
        assert exc.detail == "PERMISSION_DENIED"
    else:
        raise AssertionError("Expected permission denial")

    statement = db.scalar.call_args.args[0]
    compiled = statement.compile()
    assert "facilities.status" in str(compiled)
    assert "ACTIVE" in compiled.params.values()
