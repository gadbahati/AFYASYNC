"""Patient portal authentication — identity lookup, self-service register, login."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import randbelow
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.patient_models import PatientPasswordResetToken
from app.auth.patient_schemas import (
    PatientLoginRequest,
    PatientPasswordResetConfirm,
    PatientPasswordResetRequest,
    PatientRegisterRequest,
)
from app.auth.security import hash_password, verify_password
from app.auth.service import issue_access_token, issue_refresh_token
from app.coverage.models import Coverage
from app.patients.models import AfyaIdentity, Person
from app.rbac.models import User

RESET_CODE_TTL_MINUTES = 15
AFYA_ID_MAX_LEN = 20


def _hash_code(code: str) -> str:
    return sha256(code.encode("utf-8")).hexdigest()


def _mask_destination(value: str, channel: str) -> str:
    if channel == "EMAIL" and "@" in value:
        local, _, domain = value.partition("@")
        return f"{local[:2]}***@{domain}"
    digits = "".join(c for c in value if c.isdigit())
    if len(digits) >= 4:
        return f"***{digits[-4:]}"
    return "***"


def _normalize_afya_id(raw: str) -> str:
    cleaned = raw.strip().upper()
    if len(cleaned) > AFYA_ID_MAX_LEN:
        cleaned = cleaned[:AFYA_ID_MAX_LEN]
    return cleaned


def _find_person_by_afya_id(db: Session, afya_id: str) -> tuple[Person, AfyaIdentity] | None:
    raw = afya_id.strip()
    candidates = [raw, raw.upper(), _normalize_afya_id(raw)]
    for candidate in candidates:
        identity = db.scalar(
            select(AfyaIdentity).where(
                AfyaIdentity.afya_id == candidate,
                AfyaIdentity.status == "ACTIVE",
            )
        )
        if identity is not None:
            person = db.get(Person, identity.person_id)
            if person is not None and person.status == "ACTIVE":
                return person, identity
    return None


def _find_person_by_membership(db: Session, membership_number: str) -> Person | None:
    coverage = db.scalar(
        select(Coverage).where(
            Coverage.membership_number == membership_number.strip(),
            Coverage.status == "ACTIVE",
        )
    )
    if coverage is None:
        return None
    person_id = getattr(coverage, "person_id", None) or getattr(coverage, "patient_id", None)
    if person_id is None:
        return None
    person = db.get(Person, person_id)
    if person is None or person.status != "ACTIVE":
        return None
    return person


def resolve_patient_by_identifier(db: Session, identifier: str) -> tuple[Person, AfyaIdentity | None]:
    raw = identifier.strip()
    found = _find_person_by_afya_id(db, raw)
    if found is not None:
        return found[0], found[1]

    person = _find_person_by_membership(db, raw)
    if person is not None:
        identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
        return person, identity

    raise ValueError("PATIENT_NOT_FOUND")


def get_or_create_patient_user(db: Session, person: Person, identity: AfyaIdentity | None) -> User:
    user = db.scalar(select(User).where(User.person_id == person.id))
    if user is not None:
        return user

    username = identity.afya_id if identity else f"patient-{str(person.id)[:8]}"
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise ValueError("USERNAME_CONFLICT")

    user = User(
        person_id=person.id,
        username=username,
        phone=person.phone,
        password_hash=None,
        status="ACTIVE",
    )
    db.add(user)
    db.flush()
    return user


def _create_person_and_identity(
    db: Session,
    *,
    afya_id: str,
    first_name: str,
    last_name: str,
    phone: str | None,
    email: str | None,
) -> tuple[Person, AfyaIdentity]:
    person = Person(
        first_name=first_name.strip() or "Patient",
        last_name=last_name.strip() or "User",
        phone=(phone or "").strip() or None,
        email=(email or "").strip() or None,
        sex="UNKNOWN",
        status="ACTIVE",
    )
    db.add(person)
    db.flush()

    identity = AfyaIdentity(
        person_id=person.id,
        afya_id=afya_id,
        status="ACTIVE",
    )
    db.add(identity)
    db.flush()
    return person, identity


def register_patient(
    db: Session,
    *,
    payload: PatientRegisterRequest,
    ip_address: str | None = None,
) -> User:
    afya_id = _normalize_afya_id(payload.afya_id)
    if len(afya_id) < 3:
        raise ValueError("INVALID_AFYA_ID")

    found = _find_person_by_afya_id(db, afya_id)
    if found is None:
        # Self-service: create person + Afya identity for a new portal account
        first = (payload.first_name or "").strip()
        last = (payload.last_name or "").strip()
        if not first or not last:
            raise ValueError("NAME_REQUIRED_FOR_NEW_ACCOUNT")
        person, identity = _create_person_and_identity(
            db,
            afya_id=afya_id,
            first_name=first,
            last_name=last,
            phone=payload.phone,
            email=payload.email,
        )
    else:
        person, identity = found

    user = db.scalar(select(User).where(User.person_id == person.id))
    if user is not None and user.password_hash:
        raise ValueError("ACCOUNT_ALREADY_EXISTS")

    if user is None:
        user = get_or_create_patient_user(db, person, identity)

    user.password_hash = hash_password(payload.password)
    user.status = "ACTIVE"
    user.username = identity.afya_id
    if payload.phone:
        user.phone = payload.phone.strip()
        if not person.phone:
            person.phone = payload.phone.strip()
    if payload.email and not person.email:
        person.email = payload.email.strip()

    db.add(user)
    db.add(person)
    db.flush()

    record_audit(
        db,
        action="PATIENT_REGISTER",
        resource_type="USER",
        resource_id=str(user.id),
        result="SUCCESS",
        user_id=user.id,
        patient_id=person.id,
        ip_address=ip_address,
        metadata={"afya_id": identity.afya_id},
        commit=False,
    )
    return user


def login_patient(
    db: Session,
    *,
    payload: PatientLoginRequest,
    ip_address: str | None = None,
) -> tuple[User, str, str, int]:
    from app.config import settings

    try:
        person, identity = resolve_patient_by_identifier(db, payload.identifier)
    except ValueError:
        raise ValueError("INVALID_CREDENTIALS") from None

    user = db.scalar(select(User).where(User.person_id == person.id))
    if user is None or user.status != "ACTIVE" or not user.password_hash:
        raise ValueError("INVALID_CREDENTIALS")

    if not verify_password(payload.password, user.password_hash):
        record_audit(
            db,
            action="PATIENT_LOGIN",
            resource_type="USER",
            result="FAILURE",
            user_id=user.id,
            patient_id=person.id,
            ip_address=ip_address,
            commit=True,
        )
        raise ValueError("INVALID_CREDENTIALS")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.flush()

    access = issue_access_token(user, facility_id=None)
    refresh = issue_refresh_token(db, user, facility_id=None)

    record_audit(
        db,
        action="PATIENT_LOGIN",
        resource_type="USER",
        result="SUCCESS",
        user_id=user.id,
        patient_id=person.id,
        ip_address=ip_address,
        commit=False,
    )

    return user, access, refresh, settings.access_token_minutes * 60


def request_password_reset(
    db: Session,
    *,
    payload: PatientPasswordResetRequest,
    ip_address: str | None = None,
) -> tuple[str, str, str, str]:
    """Returns (channel, destination_hint, plain_code, destination).

    plain_code and destination must never be returned in the HTTP body.
    """
    try:
        person, _identity = resolve_patient_by_identifier(db, payload.identifier)
    except ValueError:
        return payload.channel, "***", "", ""

    user = db.scalar(select(User).where(User.person_id == person.id))
    if user is None or not user.password_hash:
        return payload.channel, "***", "", ""

    if payload.channel == "EMAIL":
        destination = (person.email or "").strip()
        if not destination:
            raise ValueError("NO_EMAIL_ON_FILE")
    else:
        destination = (user.phone or person.phone or "").strip()
        if not destination:
            raise ValueError("NO_PHONE_ON_FILE")

    now = datetime.now(timezone.utc)
    db.execute(
        update(PatientPasswordResetToken)
        .where(
            PatientPasswordResetToken.user_id == user.id,
            PatientPasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    code = f"{randbelow(1_000_000):06d}"
    token = PatientPasswordResetToken(
        user_id=user.id,
        code_hash=_hash_code(code),
        channel=payload.channel,
        destination=destination,
        expires_at=now + timedelta(minutes=RESET_CODE_TTL_MINUTES),
    )
    db.add(token)
    db.flush()

    record_audit(
        db,
        action="PATIENT_PASSWORD_RESET_REQUESTED",
        resource_type="USER",
        resource_id=str(user.id),
        result="SUCCESS",
        user_id=user.id,
        patient_id=person.id,
        ip_address=ip_address,
        metadata={"channel": payload.channel},
        commit=False,
    )

    return payload.channel, _mask_destination(destination, payload.channel), code, destination


def confirm_password_reset(
    db: Session,
    *,
    payload: PatientPasswordResetConfirm,
    ip_address: str | None = None,
) -> None:
    try:
        person, _identity = resolve_patient_by_identifier(db, payload.identifier)
    except ValueError:
        raise ValueError("INVALID_RESET_CODE") from None

    user = db.scalar(select(User).where(User.person_id == person.id))
    if user is None:
        raise ValueError("INVALID_RESET_CODE")

    now = datetime.now(timezone.utc)
    token = db.scalar(
        select(PatientPasswordResetToken)
        .where(
            PatientPasswordResetToken.user_id == user.id,
            PatientPasswordResetToken.used_at.is_(None),
            PatientPasswordResetToken.expires_at > now,
            PatientPasswordResetToken.code_hash == _hash_code(payload.code.strip()),
        )
        .order_by(PatientPasswordResetToken.created_at.desc())
    )
    if token is None:
        raise ValueError("INVALID_RESET_CODE")

    token.used_at = now
    user.password_hash = hash_password(payload.new_password)
    db.add(token)
    db.add(user)
    db.flush()

    db.execute(
        update(PatientPasswordResetToken)
        .where(
            PatientPasswordResetToken.user_id == user.id,
            PatientPasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    record_audit(
        db,
        action="PATIENT_PASSWORD_RESET_CONFIRMED",
        resource_type="USER",
        resource_id=str(user.id),
        result="SUCCESS",
        user_id=user.id,
        patient_id=person.id,
        ip_address=ip_address,
        commit=False,
    )
