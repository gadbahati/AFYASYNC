from hashlib import sha256
from hmac import compare_digest, new
from time import time

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from app.config import settings

router = APIRouter(prefix="/api/v1/ussd", tags=["USSD"])


class USSDRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=7, max_length=32)
    text: str = Field(default="", max_length=160)
    service_code: str = Field(default="", max_length=32)


def _secret() -> str:
    value = getattr(settings, "ussd_webhook_secret", "")
    if not value or value == "change-this-development-secret":
        raise HTTPException(status_code=503, detail="USSD_PROVIDER_NOT_CONFIGURED")
    return value


def _verify(timestamp: str, signature: str, body: bytes) -> None:
    try:
        sent = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_TIMESTAMP") from exc
    if abs(time() - sent) > 300:
        raise HTTPException(status_code=401, detail="WEBHOOK_TIMESTAMP_EXPIRED")
    expected = new(_secret().encode(), f"{timestamp}.".encode() + body, sha256).hexdigest()
    if not compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_SIGNATURE")


def _response(text: str, end: bool = False) -> PlainTextResponse:
    return PlainTextResponse(("END " if end else "CON ") + text)


@router.post("/callback", response_class=PlainTextResponse)
async def callback(
    request: Request,
    x_afasync_timestamp: str = Header(..., alias="X-AfyaSync-Timestamp"),
    x_afasync_signature: str = Header(..., alias="X-AfyaSync-Signature"),
):
    body = await request.body()
    _verify(x_afasync_timestamp, x_afasync_signature, body)
    try:
        payload = USSDRequest.model_validate_json(body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="INVALID_USSD_REQUEST") from exc

    # Provider-neutral boundary: no patient data is disclosed from an
    # unauthenticated phone number. Real member services require a contracted
    # provider, approved service catalogue and explicit member authentication.
    choice = payload.text.strip().split("*")[-1] if payload.text.strip() else ""
    if not choice:
        return _response("AfyaSync\n1. Member services\n2. Facility services\n0. Exit")
    if choice == "0":
        return _response("Thank you for using AfyaSync.", end=True)
    if choice in {"1", "2"}:
        return _response("This service is not activated for this provider.", end=True)
    return _response("Invalid choice. Please try again.")
