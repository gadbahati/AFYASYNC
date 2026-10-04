"""Phase 131 — discharge encounter workflow. Developed by BAHATI GAD WANGWE."""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.discharge_models import ClinicalDischarge
from app.encounters.models import Encounter

ALLOWED_DISPOSITIONS = {
    "HOME",
    "TRANSFER",
    "ADMIT",
    "LEFT_AMA",
    "DIED",
    "ABSCONDED",
    "REFERRED",
}
ALLOWED_OUTCOMES = {"STABLE", "IMPROVED", "WORSENED", "DECEASED", "UNKNOWN"}


class DischargeError(ValueError):
    pass


def get_discharge(db: Session, *, encounter_id: UUID, facility_id: UUID) -> ClinicalDischarge | None:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise DischargeError("ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise DischargeError("FACILITY_ACCESS_DENIED")
    return db.scalar(select(ClinicalDischarge).where(ClinicalDischarge.encounter_id == encounter_id))


def discharge_encounter(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    disposition: str,
    outcome: str = "STABLE",
    follow_up_instructions: str | None = None,
    follow_up_date: date | None = None,
    discharge_summary: str | None = None,
) -> ClinicalDischarge:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise DischargeError("ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise DischargeError("FACILITY_ACCESS_DENIED")
    if enc.status in {"CLOSED", "DISCHARGED", "CANCELLED"}:
        raise DischargeError("ENCOUNTER_ALREADY_CLOSED")

    disposition = (disposition or "").strip().upper()
    outcome = (outcome or "STABLE").strip().upper()
    if disposition not in ALLOWED_DISPOSITIONS:
        raise DischargeError("INVALID_DISPOSITION")
    if outcome not in ALLOWED_OUTCOMES:
        raise DischargeError("INVALID_OUTCOME")

    existing = db.scalar(select(ClinicalDischarge).where(ClinicalDischarge.encounter_id == encounter_id))
    if existing is not None:
        raise DischargeError("DISCHARGE_ALREADY_RECORDED")

    now = datetime.now(timezone.utc)
    row = ClinicalDischarge(
        encounter_id=enc.id,
        facility_id=enc.facility_id,
        patient_id=enc.patient_id,
        disposition=disposition,
        outcome=outcome,
        follow_up_instructions=(follow_up_instructions or None),
        follow_up_date=follow_up_date,
        discharge_summary=(discharge_summary or None),
        discharged_by=actor_user_id,
        discharged_at=now,
    )
    enc.status = "DISCHARGED"
    enc.ended_at = now
    db.add(row)
    record_audit(
        db,
        action="DISCHARGE_ENCOUNTER",
        resource_type="CLINICAL_DISCHARGE",
        resource_id=str(enc.id),
        result="DISCHARGED",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=enc.patient_id,
        metadata={
            "disposition": disposition,
            "outcome": outcome,
            "encounter_id": enc.encounter_id,
        },
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row
