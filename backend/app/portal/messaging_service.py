"""Appointment requests and template-safe facility messaging."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.notifications.events import notify_patient_event
from app.notifications.models import Notification
from app.portal.message_templates import list_templates_for, render_template
from app.portal.messaging_models import AppointmentRequest, FacilityMessage
from app.rbac.models import Staff, User

MAX_REASON = 2000
MAX_MESSAGE = 5000
MAX_PENDING_PER_FACILITY = 10
# Patient may not free-type; facility may use templates (preferred) or short free text
FACILITY_FREE_TEXT_MAX = 500
PATIENT_MSG_RATE_LIMIT = 20  # per rolling hour per patient+facility


def list_bookable_facilities(db: Session) -> list[Facility]:
    return list(
        db.scalars(
            select(Facility)
            .where(Facility.status == "ACTIVE")
            .order_by(Facility.name.asc())
        )
    )


def list_facility_departments(db: Session, facility_id: UUID) -> list[Department]:
    return list(
        db.scalars(
            select(Department)
            .where(Department.facility_id == facility_id, Department.status == "ACTIVE")
            .order_by(Department.name.asc())
        )
    )


def _staff_users_at_facility(db: Session, facility_id: UUID) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .join(Staff, Staff.person_id == User.person_id)
            .where(
                Staff.facility_id == facility_id,
                Staff.status == "ACTIVE",
                User.status == "ACTIVE",
                User.person_id.is_not(None),
            )
            .distinct()
        )
    )


def _notify_facility_staff(
    db: Session,
    *,
    facility_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    action_url: str,
    metadata: dict,
    priority: str = "NORMAL",
) -> None:
    for u in _staff_users_at_facility(db, facility_id):
        db.add(
            Notification(
                user_id=u.id,
                person_id=None,
                facility_id=facility_id,
                notification_type=notification_type,
                title=title,
                message=message[:500],
                priority=priority,
                action_url=action_url,
                metadata_json=metadata,
            )
        )


def create_appointment_request(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    reason: str,
    preferred_date: datetime | None = None,
    department_id: UUID | None = None,
    patient_notes: str | None = None,
    actor_user_id: UUID,
) -> AppointmentRequest:
    facility = db.get(Facility, facility_id)
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")

    reason_clean = (reason or "").strip()
    if len(reason_clean) < 5:
        raise ValueError("REASON_TOO_SHORT")
    if len(reason_clean) > MAX_REASON:
        raise ValueError("REASON_TOO_LONG")

    if department_id is not None:
        dept = db.get(Department, department_id)
        if dept is None or dept.facility_id != facility_id or dept.status != "ACTIVE":
            raise ValueError("DEPARTMENT_NOT_FOUND")

    open_pending = list(
        db.scalars(
            select(AppointmentRequest).where(
                AppointmentRequest.patient_id == patient_id,
                AppointmentRequest.facility_id == facility_id,
                AppointmentRequest.status == "PENDING",
            )
        )
    )
    if len(open_pending) >= MAX_PENDING_PER_FACILITY:
        raise ValueError("TOO_MANY_PENDING_REQUESTS")

    notes_clean = patient_notes.strip() if patient_notes else None
    if notes_clean and len(notes_clean) > MAX_REASON:
        notes_clean = notes_clean[:MAX_REASON]

    req = AppointmentRequest(
        patient_id=patient_id,
        facility_id=facility_id,
        department_id=department_id,
        preferred_date=preferred_date,
        reason=reason_clean,
        patient_notes=notes_clean,
        status="PENDING",
    )
    db.add(req)
    db.flush()

    _notify_facility_staff(
        db,
        facility_id=facility_id,
        notification_type="APPOINTMENT_REQUEST",
        title="New appointment request",
        message=f"A patient requested an appointment: {reason_clean[:120]}",
        action_url="/appointments",
        metadata={"request_id": str(req.id), "patient_id": str(patient_id)},
        priority="HIGH",
    )

    record_audit(
        db,
        action="APPOINTMENT_REQUEST_CREATED",
        resource_type="AppointmentRequest",
        resource_id=str(req.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        commit=False,
    )
    return req


def list_patient_requests(db: Session, patient_id: UUID) -> list[AppointmentRequest]:
    return list(
        db.scalars(
            select(AppointmentRequest)
            .where(AppointmentRequest.patient_id == patient_id)
            .order_by(AppointmentRequest.created_at.desc())
        )
    )


def list_facility_requests(
    db: Session, facility_id: UUID, status: str | None = None
) -> list[AppointmentRequest]:
    stmt = select(AppointmentRequest).where(AppointmentRequest.facility_id == facility_id)
    if status:
        stmt = stmt.where(AppointmentRequest.status == status.upper())
    return list(db.scalars(stmt.order_by(AppointmentRequest.created_at.desc())))


def respond_to_request(
    db: Session,
    *,
    request_id: UUID,
    facility_id: UUID,
    decision: str,
    offered_appointment_at: datetime | None,
    response_notes: str | None,
    department_id: UUID | None,
    actor_user_id: UUID,
) -> AppointmentRequest:
    req = db.get(AppointmentRequest, request_id)
    if req is None or req.facility_id != facility_id:
        raise ValueError("REQUEST_NOT_FOUND")
    if req.status != "PENDING":
        raise ValueError("REQUEST_NOT_PENDING")

    decision = decision.upper()
    if decision not in {"ACCEPTED", "DECLINED", "RESCHEDULED"}:
        raise ValueError("INVALID_DECISION")

    if decision in {"ACCEPTED", "RESCHEDULED"} and offered_appointment_at is None:
        raise ValueError("OFFERED_TIME_REQUIRED")

    if offered_appointment_at is not None:
        now = datetime.now(timezone.utc)
        if offered_appointment_at.tzinfo is None:
            offered_appointment_at = offered_appointment_at.replace(tzinfo=timezone.utc)
        if offered_appointment_at < now:
            raise ValueError("OFFERED_TIME_IN_PAST")

    notes = (response_notes or "").strip() or None
    if notes and len(notes) > MAX_REASON:
        notes = notes[:MAX_REASON]

    req.status = decision
    req.facility_response_notes = notes
    req.offered_appointment_at = offered_appointment_at
    req.responded_by = actor_user_id
    req.responded_at = datetime.now(timezone.utc)

    if decision in {"ACCEPTED", "RESCHEDULED"} and offered_appointment_at is not None:
        dept_id = department_id or req.department_id
        if dept_id is None:
            dept = db.scalar(
                select(Department)
                .where(Department.facility_id == facility_id, Department.status == "ACTIVE")
                .limit(1)
            )
            if dept is None:
                raise ValueError("NO_DEPARTMENT")
            dept_id = dept.id
        else:
            dept = db.get(Department, dept_id)
            if dept is None or dept.facility_id != facility_id:
                raise ValueError("DEPARTMENT_NOT_FOUND")

        appt = Appointment(
            patient_id=req.patient_id,
            facility_id=facility_id,
            department_id=dept_id,
            appointment_at=offered_appointment_at,
            reason=req.reason,
            status="SCHEDULED",
        )
        db.add(appt)
        db.flush()
        req.appointment_id = appt.id

        notify_patient_event(
            db,
            patient_id=req.patient_id,
            facility_id=facility_id,
            event_type="APPOINTMENT_CONFIRMED",
            action_url="/portal/book",
            metadata={
                "request_id": str(req.id),
                "appointment_id": str(appt.id),
                "decision": decision,
            },
            actor_user_id=actor_user_id,
            commit=False,
        )
    else:
        notify_patient_event(
            db,
            patient_id=req.patient_id,
            facility_id=facility_id,
            event_type="APPOINTMENT_DECLINED",
            action_url="/portal/book",
            metadata={"request_id": str(req.id), "decision": decision},
            actor_user_id=actor_user_id,
            commit=False,
        )

    record_audit(
        db,
        action="APPOINTMENT_REQUEST_RESPONDED",
        resource_type="AppointmentRequest",
        resource_id=str(req.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=req.patient_id,
        metadata={"decision": decision},
        commit=False,
    )
    return req


def cancel_patient_request(
    db: Session, *, request_id: UUID, patient_id: UUID, actor_user_id: UUID
) -> AppointmentRequest:
    req = db.get(AppointmentRequest, request_id)
    if req is None or req.patient_id != patient_id:
        raise ValueError("REQUEST_NOT_FOUND")
    if req.status != "PENDING":
        raise ValueError("REQUEST_NOT_PENDING")
    req.status = "CANCELLED_BY_PATIENT"
    db.add(req)
    record_audit(
        db,
        action="APPOINTMENT_REQUEST_CANCELLED",
        resource_type="AppointmentRequest",
        resource_id=str(req.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=req.facility_id,
        patient_id=patient_id,
        commit=False,
    )
    return req


def _patient_rate_ok(db: Session, *, patient_id: UUID, facility_id: UUID) -> bool:
    since = datetime.now(timezone.utc) - timedelta(hours=1)
    count = db.scalar(
        select(func.count())
        .select_from(FacilityMessage)
        .where(
            FacilityMessage.patient_id == patient_id,
            FacilityMessage.facility_id == facility_id,
            FacilityMessage.sender_type == "PATIENT",
            FacilityMessage.created_at >= since,
        )
    )
    return int(count or 0) < PATIENT_MSG_RATE_LIMIT


def send_message(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    sender_type: str,
    sender_user_id: UUID,
    template_code: str | None = None,
    slots: dict[str, str] | None = None,
    body: str | None = None,
    related_request_id: UUID | None = None,
) -> FacilityMessage:
    """Phase 13: patients MUST use templates; facility prefers templates, short free text allowed."""
    if sender_type not in {"PATIENT", "FACILITY"}:
        raise ValueError("INVALID_SENDER")
    facility = db.get(Facility, facility_id)
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")

    if sender_type == "PATIENT":
        if not template_code:
            raise ValueError("TEMPLATE_REQUIRED")
        if not _patient_rate_ok(db, patient_id=patient_id, facility_id=facility_id):
            raise ValueError("RATE_LIMITED")
        code, text = render_template(
            sender_type="PATIENT", template_code=template_code, slots=slots
        )
    else:
        # Facility: template preferred; free text only if short and no template
        if template_code:
            code, text = render_template(
                sender_type="FACILITY", template_code=template_code, slots=slots
            )
        else:
            text = (body or "").strip()
            if not text:
                raise ValueError("EMPTY_MESSAGE")
            if len(text) > FACILITY_FREE_TEXT_MAX:
                raise ValueError("MESSAGE_TOO_LONG")
            code = None

    if related_request_id is not None:
        req = db.get(AppointmentRequest, related_request_id)
        if req is None or req.patient_id != patient_id or req.facility_id != facility_id:
            raise ValueError("INVALID_RELATED_REQUEST")

    msg = FacilityMessage(
        patient_id=patient_id,
        facility_id=facility_id,
        sender_type=sender_type,
        sender_user_id=sender_user_id,
        body=text[:MAX_MESSAGE],
        template_code=code,
        related_request_id=related_request_id,
    )
    db.add(msg)
    db.flush()

    if sender_type == "PATIENT":
        _notify_facility_staff(
            db,
            facility_id=facility_id,
            notification_type="PATIENT_MESSAGE",
            title="Message from patient",
            message=text[:200],
            action_url="/messages",
            metadata={
                "message_id": str(msg.id),
                "patient_id": str(patient_id),
                "template_code": code,
            },
        )
    else:
        notify_patient_event(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            event_type="FACILITY_MESSAGE",
            action_url="/portal/messages",
            metadata={"message_id": str(msg.id), "template_code": code},
            actor_user_id=sender_user_id,
            commit=False,
        )

    record_audit(
        db,
        action="FACILITY_MESSAGE_SENT",
        resource_type="FacilityMessage",
        resource_id=str(msg.id),
        result="SUCCESS",
        user_id=sender_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"sender_type": sender_type, "template_code": code},
        commit=False,
    )
    return msg


def list_thread(
    db: Session, *, patient_id: UUID, facility_id: UUID
) -> list[FacilityMessage]:
    return list(
        db.scalars(
            select(FacilityMessage)
            .where(
                FacilityMessage.patient_id == patient_id,
                FacilityMessage.facility_id == facility_id,
            )
            .order_by(FacilityMessage.created_at.asc())
        )
    )


def list_patient_threads(db: Session, patient_id: UUID) -> list[dict]:
    messages = list(
        db.scalars(
            select(FacilityMessage)
            .where(FacilityMessage.patient_id == patient_id)
            .order_by(FacilityMessage.created_at.desc())
        )
    )
    seen: set[UUID] = set()
    threads: list[dict] = []
    for m in messages:
        if m.facility_id in seen:
            continue
        seen.add(m.facility_id)
        facility = db.get(Facility, m.facility_id)
        threads.append(
            {
                "facility_id": m.facility_id,
                "facility_name": facility.name if facility else "Facility",
                "last_message": m.body[:120],
                "last_at": m.created_at,
                "sender_type": m.sender_type,
            }
        )
    return threads


def list_facility_inbox(db: Session, facility_id: UUID) -> list[dict]:
    messages = list(
        db.scalars(
            select(FacilityMessage)
            .where(FacilityMessage.facility_id == facility_id)
            .order_by(FacilityMessage.created_at.desc())
        )
    )
    seen: set[UUID] = set()
    threads: list[dict] = []
    for m in messages:
        if m.patient_id in seen:
            continue
        seen.add(m.patient_id)
        from app.patients.models import Person

        person = db.get(Person, m.patient_id)
        name = (
            f"{person.first_name} {person.last_name}".strip()
            if person
            else str(m.patient_id)
        )
        threads.append(
            {
                "patient_id": str(m.patient_id),
                "patient_name": name,
                "last_message": m.body[:120],
                "last_at": m.created_at,
                "sender_type": m.sender_type,
            }
        )
    return threads
