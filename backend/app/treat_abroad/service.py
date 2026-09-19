"""Service layer for SHA Treat Abroad cases — hardened."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import Person
from app.treat_abroad.models import ApprovedOverseasProcedure, OverseasTreatmentCase
from app.treat_abroad.schemas import OverseasCaseCreate, OverseasCaseUpdate

ALLOWED_TRANSITIONS = {
    "DRAFT": {"SUBMITTED"},
    "SUBMITTED": {"UNDER_REVIEW", "REJECTED"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED"},
    "APPROVED": {"TRAVEL_ARRANGED", "REJECTED"},
    "REJECTED": {"CLOSED"},
    "TRAVEL_ARRANGED": {"TREATMENT_IN_PROGRESS"},
    "TREATMENT_IN_PROGRESS": {"RETURNED"},
    "RETURNED": {"CLOSED"},
    "CLOSED": set(),  # terminal — no further status changes
}

MAX_OPEN_CASES_PER_PATIENT = 20


def _case_number() -> str:
    return f"OTA-{uuid4().hex[:10].upper()}"


def list_approved_procedures(db: Session, *, active_only: bool = True) -> list[ApprovedOverseasProcedure]:
    stmt = select(ApprovedOverseasProcedure)
    if active_only:
        stmt = stmt.where(ApprovedOverseasProcedure.is_active.is_(True))
    return list(db.scalars(stmt.order_by(ApprovedOverseasProcedure.name.asc())))


def create_case(
    db: Session,
    *,
    payload: OverseasCaseCreate,
    created_by: UUID,
) -> OverseasTreatmentCase:
    person = db.get(Person, payload.patient_id)
    if person is None or person.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")

    procedure = db.get(ApprovedOverseasProcedure, payload.procedure_id)
    if procedure is None or not procedure.is_active:
        raise ValueError("PROCEDURE_NOT_FOUND_OR_INACTIVE")

    open_count = len(
        list(
            db.scalars(
                select(OverseasTreatmentCase).where(
                    OverseasTreatmentCase.patient_id == payload.patient_id,
                    OverseasTreatmentCase.status.not_in({"CLOSED", "REJECTED"}),
                )
            )
        )
    )
    if open_count >= MAX_OPEN_CASES_PER_PATIENT:
        raise ValueError("TOO_MANY_OPEN_CASES")

    summary = payload.clinical_summary.strip()[:8000]
    local_reason = payload.local_unavailability_reason.strip()[:4000]
    if len(summary) < 20:
        raise ValueError("CLINICAL_SUMMARY_TOO_SHORT")
    if len(local_reason) < 10:
        raise ValueError("LOCAL_REASON_TOO_SHORT")

    case = OverseasTreatmentCase(
        case_number=_case_number(),
        patient_id=payload.patient_id,
        facility_id=payload.facility_id,
        encounter_id=payload.encounter_id,
        procedure_id=payload.procedure_id,
        clinical_summary=summary,
        local_unavailability_reason=local_reason,
        referring_clinician_id=payload.referring_clinician_id,
        status="DRAFT",
        foreign_hospital_name=(payload.foreign_hospital_name or None),
        foreign_hospital_country=(payload.foreign_hospital_country or None),
        foreign_hospital_city=(payload.foreign_hospital_city or None),
        planned_departure_date=payload.planned_departure_date,
        created_by=created_by,
    )
    db.add(case)
    db.flush()

    record_audit(
        db,
        action="OVERSEAS_CASE_CREATED",
        resource_type="OverseasTreatmentCase",
        resource_id=str(case.id),
        result="SUCCESS",
        user_id=created_by,
        facility_id=payload.facility_id,
        patient_id=payload.patient_id,
        metadata={
            "case_number": case.case_number,
            "procedure_id": str(payload.procedure_id),
            "procedure_code": procedure.code,
        },
        commit=False,
    )
    return case


def get_case(db: Session, case_id: UUID, facility_id: UUID | None = None) -> OverseasTreatmentCase:
    case = db.get(OverseasTreatmentCase, case_id)
    if case is None:
        raise ValueError("CASE_NOT_FOUND")
    if facility_id is not None and case.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    return case


def list_cases(
    db: Session,
    *,
    facility_id: UUID | None = None,
    patient_id: UUID | None = None,
    status: str | None = None,
) -> list[OverseasTreatmentCase]:
    stmt = select(OverseasTreatmentCase)
    if facility_id is not None:
        stmt = stmt.where(OverseasTreatmentCase.facility_id == facility_id)
    if patient_id is not None:
        stmt = stmt.where(OverseasTreatmentCase.patient_id == patient_id)
    if status is not None:
        stmt = stmt.where(OverseasTreatmentCase.status == status)
    return list(db.scalars(stmt.order_by(OverseasTreatmentCase.created_at.desc())))


def update_case(
    db: Session,
    *,
    case: OverseasTreatmentCase,
    payload: OverseasCaseUpdate,
    actor_user_id: UUID,
) -> OverseasTreatmentCase:
    if case.status == "CLOSED":
        raise ValueError("CASE_CLOSED")

    previous_status = case.status

    if payload.status is not None and payload.status != case.status:
        allowed = ALLOWED_TRANSITIONS.get(case.status, set())
        if payload.status not in allowed:
            raise ValueError(f"INVALID_STATUS_TRANSITION:{case.status}->{payload.status}")
        case.status = payload.status
        if payload.status in {"APPROVED", "REJECTED"}:
            case.sha_decided_at = datetime.now(timezone.utc)

    # Cap approved amount to procedure max cover when approving
    if payload.approved_amount_kes is not None:
        procedure = db.get(ApprovedOverseasProcedure, case.procedure_id)
        max_cover = float(procedure.max_cover_kes) if procedure else 500_000.0
        amount = float(payload.approved_amount_kes)
        if amount < 0:
            raise ValueError("INVALID_AMOUNT")
        if amount > max_cover:
            raise ValueError("AMOUNT_EXCEEDS_PROCEDURE_CAP")
        case.approved_amount_kes = amount

    mutable_fields = (
        "sha_preauth_reference",
        "sha_commitment_letter_ref",
        "sha_decision_notes",
        "foreign_hospital_name",
        "foreign_hospital_country",
        "foreign_hospital_city",
        "planned_departure_date",
        "actual_departure_date",
        "treatment_start_date",
        "treatment_end_date",
        "return_date",
        "follow_up_facility_id",
        "follow_up_notes",
    )
    for field in mutable_fields:
        value = getattr(payload, field, None)
        if value is not None:
            if isinstance(value, str):
                value = value.strip() or None
            setattr(case, field, value)

    db.add(case)
    db.flush()

    record_audit(
        db,
        action="OVERSEAS_CASE_UPDATED",
        resource_type="OverseasTreatmentCase",
        resource_id=str(case.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=case.facility_id,
        patient_id=case.patient_id,
        metadata={
            "status": case.status,
            "previous_status": previous_status,
            "case_number": case.case_number,
        },
        commit=False,
    )
    return case
