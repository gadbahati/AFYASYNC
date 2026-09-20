"""USSD menu engine — no PHI without PIN; rate-limited by phone."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.continuity.models import ContinuityCard
from app.patients.models import AfyaIdentity, Person
from app.portal.messaging_models import AppointmentRequest
from app.ussd.models import UssdPin, UssdSession

SESSION_TTL_MINUTES = 5
MAX_PIN_ATTEMPTS = 5
LOCK_MINUTES = 30
MAX_REQUESTS_PER_PHONE_HOUR = 40
PIN_RE = re.compile(r"^\d{4,6}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("0") and len(digits) == 10:
        digits = "254" + digits[1:]
    if digits.startswith("254") and len(digits) == 12:
        return "+" + digits
    if digits.startswith("7") and len(digits) == 9:
        return "+254" + digits
    if raw.startswith("+") and len(digits) >= 10:
        return "+" + digits
    return "+" + digits if digits else ""


def _hash_pin(person_id: UUID, pin: str) -> str:
    material = f"afyasync-ussd:{person_id}:{pin}".encode()
    return hashlib.sha256(material).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def find_person_by_phone(db: Session, phone_e164: str) -> Person | None:
    if not phone_e164:
        return None
    # Match stored phones loosely (last 9 digits)
    tail = phone_e164[-9:]
    rows = list(db.scalars(select(Person).where(Person.phone.is_not(None), Person.status == "ACTIVE")))
    for p in rows:
        stored = normalize_phone(p.phone or "")
        if stored == phone_e164 or (p.phone and p.phone.replace(" ", "").endswith(tail)):
            return p
    return None


def get_or_create_session(db: Session, *, session_id: str, phone: str) -> UssdSession:
    phone_e164 = normalize_phone(phone)
    existing = db.scalar(select(UssdSession).where(UssdSession.session_id == session_id))
    now = _now()
    if existing:
        exp = existing.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp >= now:
            existing.expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)
            db.add(existing)
            return existing
    # new session
    person = find_person_by_phone(db, phone_e164)
    sess = UssdSession(
        session_id=session_id[:120],
        phone_e164=phone_e164[:20],
        person_id=person.id if person else None,
        state="WELCOME",
        authenticated=False,
        expires_at=now + timedelta(minutes=SESSION_TTL_MINUTES),
    )
    db.add(sess)
    db.flush()
    return sess


def rate_limit_ok(db: Session, phone_e164: str) -> bool:
    since = _now() - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(UssdSession)
        .where(UssdSession.phone_e164 == phone_e164, UssdSession.created_at >= since)
    )
    # sessions alone undercount; also count by phone on any session update — soft limit
    return int(count or 0) < MAX_REQUESTS_PER_PHONE_HOUR


def _pin_row(db: Session, person_id: UUID) -> UssdPin | None:
    return db.scalar(select(UssdPin).where(UssdPin.person_id == person_id))


def set_pin(db: Session, *, person_id: UUID, pin: str) -> None:
    if not PIN_RE.match(pin):
        raise ValueError("INVALID_PIN")
    row = _pin_row(db, person_id)
    if row is None:
        row = UssdPin(person_id=person_id, pin_hash=_hash_pin(person_id, pin))
    else:
        row.pin_hash = _hash_pin(person_id, pin)
        row.failed_attempts = 0
        row.locked_until = None
    db.add(row)


def verify_pin(db: Session, *, person_id: UUID, pin: str) -> bool:
    row = _pin_row(db, person_id)
    if row is None:
        return False
    now = _now()
    if row.locked_until:
        lu = row.locked_until
        if lu.tzinfo is None:
            lu = lu.replace(tzinfo=timezone.utc)
        if lu > now:
            raise ValueError("PIN_LOCKED")
    if _hash_pin(person_id, pin) == row.pin_hash:
        row.failed_attempts = 0
        row.locked_until = None
        db.add(row)
        return True
    row.failed_attempts = int(row.failed_attempts or 0) + 1
    if row.failed_attempts >= MAX_PIN_ATTEMPTS:
        row.locked_until = now + timedelta(minutes=LOCK_MINUTES)
        row.failed_attempts = 0
    db.add(row)
    return False


def _menu_main(person: Person | None) -> str:
    name = (person.first_name if person else "Member")[:12]
    return (
        f"AfyaSync\nHabari {name}\n"
        "1. Appointments\n"
        "2. Continuity card\n"
        "3. Book visit\n"
        "4. Afya ID\n"
        "0. Exit"
    )


def _appt_summary(db: Session, person_id: UUID) -> str:
    rows = list(
        db.scalars(
            select(AppointmentRequest)
            .where(AppointmentRequest.patient_id == person_id)
            .order_by(AppointmentRequest.created_at.desc())
            .limit(3)
        )
    )
    if not rows:
        return "No recent appointment requests.\n0. Menu"
    lines = ["Recent requests:"]
    for r in rows:
        lines.append(f"- {r.status[:12]}")
    lines.append("0. Menu")
    return "\n".join(lines)


def _continuity_tip(db: Session, person_id: UUID) -> str:
    card = db.scalar(
        select(ContinuityCard)
        .where(ContinuityCard.person_id == person_id, ContinuityCard.is_active.is_(True))
        .order_by(ContinuityCard.created_at.desc())
        .limit(1)
    )
    if not card:
        return "No active continuity card. Use portal to issue one.\n0. Menu"
    return f"Card active. Prefix {card.token_prefix}…\nShow full token only in portal.\n0. Menu"


def _afya_id(db: Session, person_id: UUID) -> str:
    ident = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))
    if not ident:
        return "No Afya ID linked.\n0. Menu"
    return f"Afya ID: {ident.afya_id}\n0. Menu"


def handle_ussd(
    db: Session,
    *,
    session_id: str,
    phone_number: str,
    text: str,
) -> tuple[str, bool]:
    """Returns (message, end_session)."""
    phone_e164 = normalize_phone(phone_number)
    if not phone_e164 or len(phone_e164) < 10:
        return "Invalid phone. Contact facility.", True

    if not rate_limit_ok(db, phone_e164):
        return "Too many requests. Try later.", True

    sess = get_or_create_session(db, session_id=session_id, phone=phone_e164)
    parts = [p for p in (text or "").strip().split("*") if p != ""]
    choice = parts[-1] if parts else ""

    person = db.get(Person, sess.person_id) if sess.person_id else None

    # --- welcome / identity ---
    if sess.state == "WELCOME":
        if person is None:
            return (
                "AfyaSync\nPhone not linked to a patient.\n"
                "Register at a facility or portal first.\n",
                True,
            )
        pin = _pin_row(db, person.id)
        if pin is None:
            sess.state = "PIN_SET"
            db.add(sess)
            return "Create USSD PIN (4-6 digits):", False
        sess.state = "PIN_ENTRY"
        db.add(sess)
        return "Enter USSD PIN:", False

    if sess.state == "PIN_SET":
        if not person:
            return "Session error.", True
        if not PIN_RE.match(choice):
            return "PIN must be 4-6 digits. Try again:", False
        set_pin(db, person_id=person.id, pin=choice)
        sess.authenticated = True
        sess.state = "MENU"
        db.add(sess)
        return _menu_main(person), False

    if sess.state == "PIN_ENTRY":
        if not person:
            return "Session error.", True
        try:
            ok = verify_pin(db, person_id=person.id, pin=choice)
        except ValueError as exc:
            if str(exc) == "PIN_LOCKED":
                return "PIN locked. Try later or use portal.", True
            raise
        if not ok:
            return "Wrong PIN. Try again:", False
        sess.authenticated = True
        sess.state = "MENU"
        db.add(sess)
        return _menu_main(person), False

    if not sess.authenticated or not person:
        sess.state = "WELCOME"
        db.add(sess)
        return "Session expired. Dial again.", True

    # --- authenticated menu ---
    if sess.state == "MENU":
        if choice == "0":
            sess.state = "DONE"
            db.add(sess)
            return "Asante. AfyaSync.", True
        if choice == "1":
            sess.state = "APPT"
            db.add(sess)
            return _appt_summary(db, person.id), False
        if choice == "2":
            return _continuity_tip(db, person.id), False
        if choice == "3":
            sess.state = "BOOK"
            db.add(sess)
            return (
                "Book reason:\n"
                "1. General clinic\n"
                "2. Follow-up\n"
                "3. Lab\n"
                "0. Menu",
                False,
            )
        if choice == "4":
            return _afya_id(db, person.id), False
        return _menu_main(person), False

    if sess.state == "APPT":
        sess.state = "MENU"
        db.add(sess)
        return _menu_main(person), False

    if sess.state == "BOOK":
        reasons = {"1": "General clinic visit", "2": "Follow-up visit", "3": "Laboratory"}
        if choice == "0":
            sess.state = "MENU"
            db.add(sess)
            return _menu_main(person), False
        if choice not in reasons:
            return "Invalid. 1-3 or 0:", False
        # Record request against first linked facility if any
        from app.patients.models import PatientFacility

        link = db.scalar(
            select(PatientFacility).where(
                PatientFacility.patient_id == person.id,
                PatientFacility.status == "ACTIVE",
            )
        )
        if link is None:
            sess.state = "MENU"
            db.add(sess)
            return "No facility linked. Visit a hospital first.\n" + _menu_main(person), False
        req = AppointmentRequest(
            patient_id=person.id,
            facility_id=link.facility_id,
            reason=reasons[choice],
            status="PENDING",
        )
        db.add(req)
        sess.state = "MENU"
        db.add(sess)
        return "Request sent. Facility will respond.\n" + _menu_main(person), False

    sess.state = "MENU"
    db.add(sess)
    return _menu_main(person), False
