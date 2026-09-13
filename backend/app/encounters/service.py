from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.patients.models import PatientFacility, Person

ALLOWED_COVERAGE_MODES = {"AFYASYNC", "SHA", "CASH", "OTHER"}


def _require_active_context(db: Session, patient_id: UUID, facility_id: UUID, department_id: UUID) -> None:
    patient = db.get(Person, patient_id)
    facility = db.get(Facility, facility_id)
    department = db.get(Department, department_id)
    if patient is None or patient.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")
    if department is None or department.facility_id != facility_id or department.status != "ACTIVE":
        raise ValueError("DEPARTMENT_NOT_FOUND")
    membership = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if membership is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")


def _resolve_coverage_fields(db: Session, data: dict) -> None:
    mode = (data.get("coverage_mode") or "CASH").upper()
    if mode not in ALLOWED_COVERAGE_MODES:
        raise ValueError("INVALID_COVERAGE_MODE")
    data["coverage_mode"] = mode

    coverage_id = data.get("coverage_id")
    if coverage_id is None:
        return

    coverage = db.get(Coverage, coverage_id)
    if coverage is None or coverage.status != "ACTIVE":
        raise ValueError("COVERAGE_NOT_FOUND")
    if coverage.person_id != data["patient_id"]:
        raise ValueError("COVERAGE_PATIENT_MISMATCH")

    payer = db.get(Payer, coverage.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_FOUND")

    # Soft consistency: if mode is AFYASYNC/SHA, prefer matching payer code when known
    code = (payer.code or "").upper()
    if mode == "AFYASYNC" and code not in {"AFYASYNC", "CASH"} and not code.startswith("AFYA"):
        # Allow attached coverage but mode remains explicit from client
        pass
    if mode == "SHA" and code not in {"SHA", "SHIF", "PHF", "ECCIF"}:
        pass


def _next_encounter_id(db: Session) -> str:
    number = db.scalar(text("SELECT nextval('afasync_encounter_seq')"))
    if number is None:
        raise RuntimeError("ENCOUNTER_SEQUENCE_UNAVAILABLE")
    return f"ENC-{datetime.now(timezone.utc):%Y%m%d}-{int(number):05d}"


def create_encounter(
    db: Session,
    data: dict,
    created_by: UUID,
    *,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> Encounter:
    _require_active_context(db, data["patient_id"], data["facility_id"], data["department_id"])
    payload = dict(data)
    _resolve_coverage_fields(db, payload)
    encounter = Encounter(encounter_id=_next_encounter_id(db), created_by=created_by, **payload)
    db.add(encounter)
    db.flush()
    if actor_user_id:
        record_audit(
            db,
            action="ENCOUNTER_CREATED",
            resource_type="ENCOUNTER",
            resource_id=str(encounter.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            metadata={
                "encounter_id": encounter.encounter_id,
                "encounter_type": encounter.encounter_type,
                "coverage_mode": encounter.coverage_mode,
                "coverage_id": str(encounter.coverage_id) if encounter.coverage_id else None,
            },
            commit=False,
        )
    if commit:
        db.commit()
        db.refresh(encounter)
    return encounter


def get_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    return encounter


def get_encounter_for_facility(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = get_encounter(db, encounter_id)
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    return encounter


def list_patient_encounters_for_facility(
    db: Session,
    patient_id: UUID,
    facility_id: UUID,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Encounter], int]:
    if facility_id is None:
        raise ValueError("FACILITY_CONTEXT_REQUIRED")
    membership = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if membership is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    filters = [Encounter.patient_id == patient_id, Encounter.facility_id == facility_id]
    total = int(db.scalar(select(func.count()).select_from(Encounter).where(*filters)) or 0)
    items = list(
        db.scalars(
            select(Encounter)
            .where(*filters)
            .order_by(Encounter.started_at.desc(), Encounter.id.desc())
            .offset(offset)
            .limit(limit)
        )
    )
    return items, total


def close_encounter(
    db: Session,
    encounter_id: UUID,
    actor_user_id: UUID | None = None,
    *,
    commit: bool = True,
) -> Encounter:
    encounter = get_encounter(db, encounter_id)
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    encounter.status = "COMPLETED"
    encounter.ended_at = datetime.now(timezone.utc)
    if actor_user_id:
        record_audit(
            db,
            action="ENCOUNTER_CLOSED",
            resource_type="ENCOUNTER",
            resource_id=str(encounter.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            commit=False,
        )
    if commit:
        db.commit()
        db.refresh(encounter)
    return encounter
