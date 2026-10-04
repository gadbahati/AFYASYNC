from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import QueueEntry
from app.audit.service import record_audit
from app.clinical.models import TriageAssessment, Vital
from app.encounters.models import Encounter
from app.rbac.models import Staff


ACUITY_PRIORITY = {
    1: "CRITICAL",
    2: "URGENT",
    3: "PRIORITY",
    4: "NORMAL",
    5: "NORMAL",
}


def _open_encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    return encounter


def _staff(db: Session, staff_id: UUID, facility_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id or staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_FOUND")
    return staff


def record_triage(
    db: Session,
    encounter_id: UUID,
    facility_id: UUID,
    staff_id: UUID,
    data: dict,
    *,
    actor_user_id: UUID | None = None,
) -> TriageAssessment:
    encounter = _open_encounter(db, encounter_id, facility_id)
    _staff(db, staff_id, facility_id)

    vital_id = data.get("vital_id")
    if vital_id:
        vital = db.get(Vital, vital_id)
        if vital is None or vital.encounter_id != encounter_id:
            raise ValueError("VITAL_NOT_FOUND")
    else:
        vital = db.scalar(
            select(Vital)
            .where(Vital.encounter_id == encounter_id)
            .order_by(Vital.recorded_at.desc(), Vital.id.desc())
            .limit(1)
        )
        vital_id = vital.id if vital else None

    acuity = int(data["acuity"])
    priority = ACUITY_PRIORITY[acuity]
    red_flags = [str(item).strip() for item in (data.get("red_flags") or []) if str(item).strip()]

    assessment = TriageAssessment(
        id=uuid4(),
        encounter_id=encounter_id,
        assessed_by=staff_id,
        vital_id=vital_id,
        acuity=acuity,
        priority=priority,
        chief_complaint=(data.get("chief_complaint") or "").strip() or None,
        red_flags=red_flags,
        disposition=data.get("disposition"),
        notes=data.get("notes"),
        assessed_at=datetime.now(timezone.utc),
    )
    db.add(assessment)
    db.flush()

    # Keep the active patient-flow queue aligned with the clinical triage decision.
    active_entries = list(
        db.scalars(
            select(QueueEntry)
            .where(
                QueueEntry.encounter_id == encounter_id,
                QueueEntry.status.in_([ "WAITING", "CALLED", "IN_SERVICE" ]),
            )
        )
    )
    for entry in active_entries:
        entry.priority = priority

    if actor_user_id:
        record_audit(
            db,
            action="CLINICAL_TRIAGE_RECORDED",
            resource_type="TRIAGE_ASSESSMENT",
            resource_id=str(assessment.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=encounter.patient_id,
            metadata={
                "encounter_id": str(encounter_id),
                "acuity": acuity,
                "priority": priority,
                "red_flag_count": len(red_flags),
                "vital_id": str(vital_id) if vital_id else None,
            },
            commit=False,
        )

    db.commit()
    db.refresh(assessment)
    return assessment


def latest_triage(db: Session, encounter_id: UUID, facility_id: UUID) -> TriageAssessment | None:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    return db.scalar(
        select(TriageAssessment)
        .where(TriageAssessment.encounter_id == encounter_id)
        .order_by(TriageAssessment.assessed_at.desc(), TriageAssessment.id.desc())
        .limit(1)
    )
