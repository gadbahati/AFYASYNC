from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.auth.security import create_refresh_token, decode_refresh_token


def test_refresh_token_contains_refresh_type_and_facility_context():
    user_id = uuid4()
    facility_id = uuid4()

    token = create_refresh_token(user_id, facility_id)
    payload = decode_refresh_token(token)

    assert payload["type"] == "refresh"
    assert payload["sub"] == str(user_id)
    assert payload["facility_id"] == str(facility_id)
    assert payload["exp"] > payload["iat"]


def test_access_token_is_rejected_as_refresh_token():
    from app.auth.security import create_access_token

    token = create_access_token(uuid4())

    with pytest.raises(HTTPException) as exc_info:
        decode_refresh_token(token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "INVALID_REFRESH_TOKEN"
