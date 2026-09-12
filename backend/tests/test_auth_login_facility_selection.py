from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

import app.auth.router as auth_router
from app.auth.router import login
from app.auth.schemas import FacilitySelectionRequired, LoginRequest, TokenResponse
from app.auth.security import decode_access_token


def _request() -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def test_login_with_multiple_facilities_returns_scope_less_token_and_facility_list(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), person_id=uuid4())
    facility_a, facility_b = uuid4(), uuid4()
    staff = [SimpleNamespace(facility_id=facility_a), SimpleNamespace(facility_id=facility_b)]
    monkeypatch.setattr(auth_router, "authenticate_user", lambda *_a, **_k: (user, staff))
    audit_mock = Mock()
    monkeypatch.setattr(auth_router, "record_audit", audit_mock)

    db = Mock()
    db.execute.return_value.all.return_value = [(facility_a, "Nairobi Clinic"), (facility_b, "Kisumu Clinic")]

    result = login(LoginRequest(username="jane", password="secret1"), _request(), db)

    assert isinstance(result, FacilitySelectionRequired)
    assert result.requires_facility_selection is True
    assert {f.facility_id for f in result.facilities} == {facility_a, facility_b}

    # The access token must authenticate get_current_user (sub set, type
    # "access") but must NOT carry a facility_id yet.
    payload = decode_access_token(result.access_token)
    assert payload["sub"] == str(user.id)
    assert payload["facility_id"] is None

    # No refresh session should be created until a facility is chosen.
    db.add.assert_not_called()
    assert audit_mock.call_args.kwargs["result"] == "FACILITY_SELECTION_REQUIRED"


def test_login_with_no_active_facility_assignment_is_rejected(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), person_id=uuid4())
    monkeypatch.setattr(auth_router, "authenticate_user", lambda *_a, **_k: (user, []))
    audit_mock = Mock()
    monkeypatch.setattr(auth_router, "record_audit", audit_mock)
    db = Mock()

    with pytest.raises(HTTPException) as exc_info:
        login(LoginRequest(username="jane", password="secret1"), _request(), db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "NO_ACTIVE_FACILITY_ASSIGNMENT"
    assert audit_mock.call_args.kwargs["result"] == "NO_ACTIVE_FACILITY_ASSIGNMENT"


def test_login_with_single_facility_still_returns_full_token_response(monkeypatch) -> None:
    user = SimpleNamespace(id=uuid4(), person_id=uuid4())
    facility_id = uuid4()
    staff = [SimpleNamespace(facility_id=facility_id)]
    monkeypatch.setattr(auth_router, "authenticate_user", lambda *_a, **_k: (user, staff))
    monkeypatch.setattr(auth_router, "record_audit", Mock())
    monkeypatch.setattr(auth_router, "issue_refresh_token", lambda *_a, **_k: "refresh-token-value")
    db = Mock()

    result = login(LoginRequest(username="jane", password="secret1"), _request(), db)

    assert isinstance(result, TokenResponse)
    payload = decode_access_token(result.access_token)
    assert payload["facility_id"] == str(facility_id)
