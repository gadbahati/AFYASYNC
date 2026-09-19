"""Real appointment requests and two-way messaging between patient and facility."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment
from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.notifications.events import notify_patient_event
from app.portal.messaging_models import AppointmentRequest, FacilityMessage
from app.rbac.models import Staff, User


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

    if department_id is not None:
        dept = db.get(Department, department_id)
        if dept is None or dept.facility_id != facility_id or dept.status != "ACTIVE":
            raise ValueError("DEPARTMENT_NOT_FOUND")

    req = AppointmentRequest(
        patient_id=patient_id,
        facility_id=facility_id,
        department_id=department_id,
        preferred_date=preferred_date,
        reason=reason.strip(),
        patient_notes=patient_notes.strip() if patient_notes else None,
        status="PENDING",
    )
    db.add(req)
    db.flush()

    # Notify facility staff via in-app notification to users with staff at that facility
    staff_users = db.scalars(
        select(User)
        .join(Staff, Staff.person_id == User.person_id)
        .where(Staff.facility_id == facility_id, Staff.status == "ACTIVE", User.status == "ACTIVE")
    ).all()
    from app.notifications.models import Notification

    for u in staff_users:
        db.add(
            Notification(
                user_id=u.id,
                person_id=None,
                facility_id=facility_id,
                notification_type="APPOINTMENT_REQUEST",
                title="New appointment request",
                message=f"A patient requested an appointment: {reason[:120]}",
                priority="HIGH",
                action_url=f"/appointments/requests/{req.id}",
                metadata_json={"request_id": str(req.id), "patient_id": str(patient_id)},
            )
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
        stmt = stmt.where(AppointmentRequest.status == status)
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
    """Facility accepts (with date), declines, or proposes a different time."""
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

    req.status = decision
    req.facility_response_notes = response_notes
    req.offered_appointment_at = offered_appointment_at
    req.responded_by = actor_user_id
    req.responded_at = datetime.now(timezone.utc)

    if decision in {"ACCEPTED", "RESCHEDULED"} and offered_appointment_at is not None:
        dept_id = department_id or req.department_id
        if dept_id is None:
            # Pick first active department at facility if none specified
            dept = db.scalar(
                select(Department)
                .where(Department.facility_id == facility_id, Department.status == "ACTIVE")
                .limit(1)
            )
            if dept is None:
                raise ValueError("NO_DEPARTMENT")
            dept_id = dept.id

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
            action_url=f"/portal/appointments",
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
            action_url=f"/portal/appointments",
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


def send_message(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    body: str,
    sender_type: str,
    sender_user_id: UUID,
    related_request_id: UUID | None = None,
) -> FacilityMessage:
    if sender_type not in {"PATIENT", "FACILITY"}:
        raise ValueError("INVALID_SENDER")
    facility = db.get(Facility, facility_id)
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")

    msg = FacilityMessage(
        patient_id=patient_id,
        facility_id=facility_id,
        sender_type=sender_type,
        sender_user_id=sender_user_id,
        body=body.strip(),
        related_request_id=related_request_id,
    )
    db.add(msg)
    db.flush()

    if sender_type == "PATIENT":
        # Notify facility staff
        staff_users = db.scalars(
            select(User)
            .join(Staff, Staff.person_id == User.person_id)
            .where(
                Staff.facility_id == facility_id,
                Staff.status == "ACTIVE",
                User.status == "ACTIVE",
            )
        ).all()
        from app.notifications.models import Notification

        for u in staff_users:
            db.add(
                Notification(
                    user_id=u.id,
                    facility_id=facility_id,
                    notification_type="PATIENT_MESSAGE",
                    title="Message from patient",
                    message=body[:200],
                    priority="NORMAL",
                    action_url=f"/messages/patient/{patient_id}",
                    metadata_json={"message_id": str(msg.id)},
                )
            )
    else:
        notify_patient_event(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            event_type="FACILITY_MESSAGE",
            action_url="/portal/messages",
            metadata={"message_id": str(msg.id)},
            actor_user_id=sender_user_id,
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
    """Distinct facilities the patient has messaged, with last message preview."""
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
