"""Issue and manage Treat Abroad return-home packages."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.notifications.events import notify_patient_event
from app.treat_abroad.models import OverseasTreatmentCase
from app.treat_abroad.return_models import OverseasReturnPackage

# Statuses from which a return package may be drafted / issued
RETURN_ELIGIBLE = {"TREATMENT_IN_PROGRESS", "RETURNED"}


def _require_text(value: str | None, *, min_len: int, max_len: int, code: str) -> str:
    text = (value or "").strip()
    if len(text) < min_len:
        raise ValueError(code)
    return text[:max_len]


def get_package_for_case(db: Session, case_id: UUID) -> OverseasReturnPackage | None:
    return db.scalar(
        select(OverseasReturnPackage).where(OverseasReturnPackage.case_id == case_id)
    )


def upsert_draft_package(
    db: Session,
    *,
    case: OverseasTreatmentCase,
    actor_user_id: UUID,
    discharge_summary: str,
    procedures_performed: str,
    medications_on_discharge: str,
    follow_up_plan: str,
    complications: str | None = None,
    foreign_report_refs: str | None = None,
    follow_up_facility_id: UUID | None = None,
    recommended_follow_up_date=None,
    rehab_required: bool = False,
    rehab_notes: str | None = None,
) -> OverseasReturnPackage:
    if case.status not in RETURN_ELIGIBLE and case.status != "RETURNED":
        # Allow draft while in treatment or already returned (amend draft only)
        if case.status not in {"TREATMENT_IN_PROGRESS"}:
            raise ValueError("CASE_NOT_ELIGIBLE_FOR_RETURN_PACKAGE")

    existing = get_package_for_case(db, case.id)
    if existing and existing.status == "ISSUED":
        raise ValueError("PACKAGE_ALREADY_ISSUED")

    discharge = _require_text(discharge_summary, min_len=30, max_len=8000, code="DISCHARGE_TOO_SHORT")
    procedures = _require_text(
        procedures_performed, min_len=10, max_len=4000, code="PROCEDURES_TOO_SHORT"
    )
    meds = _require_text(
        medications_on_discharge, min_len=5, max_len=4000, code="MEDICATIONS_TOO_SHORT"
    )
    plan = _require_text(follow_up_plan, min_len=20, max_len=4000, code="FOLLOW_UP_TOO_SHORT")

    comp = (complications or "").strip()[:4000] or None
    refs = (foreign_report_refs or "").strip()[:4000] or None
    rehab = (rehab_notes or "").strip()[:2000] or None

    if existing:
        pkg = existing
        pkg.discharge_summary = discharge
        pkg.procedures_performed = procedures
        pkg.medications_on_discharge = meds
        pkg.follow_up_plan = plan
        pkg.complications = comp
        pkg.foreign_report_refs = refs
        pkg.follow_up_facility_id = follow_up_facility_id or case.follow_up_facility_id
        pkg.recommended_follow_up_date = recommended_follow_up_date
        pkg.rehab_required = bool(rehab_required)
        pkg.rehab_notes = rehab
    else:
        pkg = OverseasReturnPackage(
            case_id=case.id,
            facility_id=case.facility_id,
            patient_id=case.patient_id,
            discharge_summary=discharge,
            procedures_performed=procedures,
            medications_on_discharge=meds,
            follow_up_plan=plan,
            complications=comp,
            foreign_report_refs=refs,
            follow_up_facility_id=follow_up_facility_id or case.follow_up_facility_id,
            recommended_follow_up_date=recommended_follow_up_date,
            rehab_required=bool(rehab_required),
            rehab_notes=rehab,
            status="DRAFT",
            created_by=actor_user_id,
        )
    db.add(pkg)
    db.flush()

    record_audit(
        db,
        action="OVERSEAS_RETURN_PACKAGE_SAVED",
        resource_type="OverseasReturnPackage",
        resource_id=str(pkg.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=case.facility_id,
        patient_id=case.patient_id,
        metadata={"case_id": str(case.id), "case_number": case.case_number},
        commit=False,
    )
    return pkg


def issue_package(
    db: Session,
    *,
    case: OverseasTreatmentCase,
    actor_user_id: UUID,
) -> OverseasReturnPackage:
    """Lock package and move case TREATMENT_IN_PROGRESS → RETURNED."""
    if case.status not in {"TREATMENT_IN_PROGRESS", "RETURNED"}:
        raise ValueError("CASE_NOT_ELIGIBLE_FOR_RETURN_PACKAGE")

    pkg = get_package_for_case(db, case.id)
    if pkg is None:
        raise ValueError("PACKAGE_REQUIRED")
    if pkg.status == "ISSUED" and case.status == "RETURNED":
        return pkg

    # Re-validate required fields
    _require_text(pkg.discharge_summary, min_len=30, max_len=8000, code="DISCHARGE_TOO_SHORT")
    _require_text(pkg.procedures_performed, min_len=10, max_len=4000, code="PROCEDURES_TOO_SHORT")
    _require_text(pkg.medications_on_discharge, min_len=5, max_len=4000, code="MEDICATIONS_TOO_SHORT")
    _require_text(pkg.follow_up_plan, min_len=20, max_len=4000, code="FOLLOW_UP_TOO_SHORT")

    now = datetime.now(timezone.utc)
    pkg.status = "ISSUED"
    pkg.issued_at = now
    pkg.issued_by = actor_user_id
    db.add(pkg)

    if case.status == "TREATMENT_IN_PROGRESS":
        case.status = "RETURNED"
        if case.return_date is None:
            from datetime import date as date_cls

            case.return_date = date_cls.today()
        if pkg.follow_up_facility_id:
            case.follow_up_facility_id = pkg.follow_up_facility_id
        if pkg.follow_up_plan:
            case.follow_up_notes = pkg.follow_up_plan[:4000]
        db.add(case)

    notify_patient_event(
        db,
        patient_id=case.patient_id,
        facility_id=case.facility_id,
        event_type="TREAT_ABROAD_RETURNED",
        action_url="/portal",
        metadata={
            "case_id": str(case.id),
            "case_number": case.case_number,
            "package_id": str(pkg.id),
        },
        actor_user_id=actor_user_id,
        commit=False,
    )

    record_audit(
        db,
        action="OVERSEAS_RETURN_PACKAGE_ISSUED",
        resource_type="OverseasReturnPackage",
        resource_id=str(pkg.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=case.facility_id,
        patient_id=case.patient_id,
        metadata={"case_number": case.case_number, "status": case.status},
        commit=False,
    )
    return pkg


def assert_can_transition_to_returned(db: Session, case: OverseasTreatmentCase) -> None:
    """Block direct RETURNED without issued package."""
    pkg = get_package_for_case(db, case.id)
    if pkg is None or pkg.status != "ISSUED":
        raise ValueError("RETURN_PACKAGE_REQUIRED")
