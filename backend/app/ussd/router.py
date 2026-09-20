"""USSD provider callback and low-bandwidth lite APIs."""

from hashlib import sha256
from hmac import compare_digest, new as hmac_new
from time import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import require_patient_identity
from app.config import settings
from app.database import get_db
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import User
from app.ussd import models as ussd_models  # noqa: F401
from app.ussd.service import handle_ussd, set_pin

router = APIRouter(prefix="/api/v1/ussd", tags=["USSD"])
lite_router = APIRouter(prefix="/api/v1/lite", tags=["Low bandwidth"])


class USSDRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(min_length=7, max_length=32)
    text: str = Field(default="", max_length=160)
    service_code: str = Field(default="", max_length=32)


class UssdPinSet(BaseModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d{4,6}$")


def _secret() -> str:
    value = (getattr(settings, "ussd_webhook_secret", "") or "").strip()
    if settings.environment == "production" and (
        not value or value == "change-this-development-secret"
    ):
        raise HTTPException(status_code=503, detail="USSD_PROVIDER_NOT_CONFIGURED")
    if not value:
        return "dev-ussd-secret-not-for-production"
    return value


def _verify(timestamp: str, signature: str, body: bytes) -> None:
    try:
        sent = int(timestamp)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_TIMESTAMP") from exc
    if abs(time() - sent) > 300:
        raise HTTPException(status_code=401, detail="WEBHOOK_TIMESTAMP_EXPIRED")
    expected = hmac_new(_secret().encode(), f"{timestamp}.".encode() + body, sha256).hexdigest()
    if not compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="INVALID_WEBHOOK_SIGNATURE")


def _response(text: str, end: bool = False) -> PlainTextResponse:
    return PlainTextResponse(("END " if end else "CON ") + text[:500])


def _parse_payload(body: bytes, form: dict | None) -> USSDRequest:
    if form:
        return USSDRequest(
            session_id=str(form.get("sessionId") or form.get("session_id") or "")[:120],
            phone_number=str(form.get("phoneNumber") or form.get("phone_number") or "")[:32],
            text=str(form.get("text") or "")[:160],
            service_code=str(form.get("serviceCode") or form.get("service_code") or "")[:32],
        )
    return USSDRequest.model_validate_json(body)


@router.post("/callback", response_class=PlainTextResponse)
async def callback(
    request: Request,
    db: Session = Depends(get_db),
    x_afasync_timestamp: str | None = Header(default=None, alias="X-AfyaSync-Timestamp"),
    x_afasync_signature: str | None = Header(default=None, alias="X-AfyaSync-Signature"),
):
    body = await request.body()
    content_type = (request.headers.get("content-type") or "").lower()

    if settings.environment == "production":
        if not x_afasync_timestamp or not x_afasync_signature:
            raise HTTPException(status_code=401, detail="WEBHOOK_SIGNATURE_REQUIRED")
        _verify(x_afasync_timestamp, x_afasync_signature, body)
    elif x_afasync_timestamp and x_afasync_signature:
        _verify(x_afasync_timestamp, x_afasync_signature, body)

    form = None
    if "application/x-www-form-urlencoded" in content_type:
        form = dict(await request.form())

    try:
        payload = _parse_payload(body if form is None else b"{}", form)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="INVALID_USSD_REQUEST") from exc

    if not payload.session_id or not payload.phone_number:
        raise HTTPException(status_code=400, detail="INVALID_USSD_REQUEST")

    try:
        message, end = handle_ussd(
            db,
            session_id=payload.session_id,
            phone_number=payload.phone_number,
            text=payload.text,
        )
        db.commit()
    except Exception:
        db.rollback()
        return _response("Service temporarily unavailable.", end=True)

    return _response(message, end=end)


@router.post("/pin")
def portal_set_ussd_pin(
    payload: UssdPinSet,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    try:
        person_id = require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=403, detail=str(err)) from err
    try:
        set_pin(db, person_id=person_id, pin=payload.pin)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "message": "USSD PIN saved"}


LITE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>AfyaSync Lite</title>
<style>
body{font-family:sans-serif;margin:12px;background:#f4f6f8;color:#17212b;line-height:1.4}
a,button{display:block;width:100%;box-sizing:border-box;margin:8px 0;padding:12px;background:#17324d;color:#fff;text-align:center;text-decoration:none;border:0;border-radius:6px;font-size:16px}
a.secondary{background:#fff;color:#17324d;border:1px solid #b8c4ce}
p{font-size:14px;color:#61707d}
h1{font-size:20px;margin:0 0 8px}
</style>
</head>
<body>
<h1>AfyaSync Lite</h1>
<p>Low-data access. Use USSD on feature phones or open the full portal on better connectivity.</p>
<a href="/login/patient">Patient sign-in</a>
<a class="secondary" href="/login/facility">Facility sign-in</a>
<a class="secondary" href="/continuity">Verify continuity card</a>
<p>USSD: dial the AfyaSync service code from your registered phone. PIN required.</p>
<p style="font-size:11px">© AfyaSync · Developed by BAHATI GAD WANGWE</p>
</body>
</html>"""


@lite_router.get("", response_class=HTMLResponse)
def lite_home() -> HTMLResponse:
    return HTMLResponse(LITE_HTML)


@lite_router.get("/health")
def lite_health():
    return {"ok": True, "channel": "lite", "ussd": True}
