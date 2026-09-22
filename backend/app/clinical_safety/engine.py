"""Clinical Safety Engine — wraps pharmacy safety + pregnancy/paeds/high-risk."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical_safety.models import MedicationSafetyFlag
from app.patients.models import Person
from app.pharmacy.models import Medication
from app.pharmacy.safety_schemas import SafetyCheckResponse, SafetyConflict
from app.pharmacy.safety_service import check_prescription_safety


def _age_years(dob: date | None, today: date | None = None) -> int | None:
    if dob is None:
        return None
    today = today or date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(0, years)


def run_clinical_safety_check(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    medication_ids: list[UUID],
    encounter_id: UUID | None = None,
    patient_is_pregnant: bool | None = None,
    actor_user_id: UUID | None = None,
) -> SafetyCheckResponse:
    """Full prescribe-time safety: allergy/DDI/duplicate + catalogue flags."""
    base = check_prescription_safety(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        medication_ids=medication_ids,
        encounter_id=encounter_id,
    )
    conflicts = list(base.conflicts)
    notes = list(base.notes)

    person = db.get(Person, patient_id)
    age = _age_years(person.date_of_birth if person else None)

    for mid in medication_ids:
        med = db.get(Medication, mid)
        if med is None:
            continue
        flag = db.scalar(
            select(MedicationSafetyFlag).where(
                MedicationSafetyFlag.medication_id == mid,
                MedicationSafetyFlag.status == "ACTIVE",
            )
        )
        if flag is None:
            continue

        if flag.black_box:
            conflicts.append(
                SafetyConflict(
                    code="BLACK_BOX_WARNING",
                    severity="HIGH",
                    title="Black-box warning medication",
                    detail=flag.notes
                    or f"{med.name} carries a black-box / high-alert warning. Confirm indication and monitoring.",
                    medication_id=mid,
                    medication_name=med.name,
                    blocking=False,
                )
            )

        if flag.high_risk:
            conflicts.append(
                SafetyConflict(
                    code="HIGH_RISK_MEDICATION",
                    severity="MEDIUM",
                    title="High-risk medicine",
                    detail=f"{med.name} is flagged as high-risk. Use independent double-check where required.",
                    medication_id=mid,
                    medication_name=med.name,
                    blocking=False,
                )
            )

        if flag.paediatric_caution and age is not None and age < 12:
            conflicts.append(
                SafetyConflict(
                    code="PAEDIATRIC_CAUTION",
                    severity="HIGH",
                    title="Paediatric dosing caution",
                    detail=(
                        f"Patient age {age} years. {med.name} requires paediatric dose verification "
                        f"(weight-based dosing recommended)."
                    ),
                    medication_id=mid,
                    medication_name=med.name,
                    blocking=False,
                )
            )

        if patient_is_pregnant and flag.pregnancy_category in {"D", "X"}:
            conflicts.append(
                SafetyConflict(
                    code="PREGNANCY_CONTRAINDICATION",
                    severity="CRITICAL" if flag.pregnancy_category == "X" else "HIGH",
                    title="Pregnancy safety concern",
                    detail=(
                        f"{med.name} pregnancy category {flag.pregnancy_category}. "
                        + ("Contraindicated in pregnancy." if flag.pregnancy_category == "X" else "Use only if benefit outweighs risk; document counselling.")
                    ),
                    medication_id=mid,
                    medication_name=med.name,
                    blocking=flag.pregnancy_category == "X",
                )
            )

        if flag.renal_caution:
            conflicts.append(
                SafetyConflict(
                    code="RENAL_CAUTION",
                    severity="MEDIUM",
                    title="Renal impairment caution",
                    detail=f"{med.name} may require dose adjustment in renal impairment. Confirm renal status.",
                    medication_id=mid,
                    medication_name=med.name,
                    blocking=False,
                )
            )

    blocking_count = sum(1 for c in conflicts if c.blocking)
    warning_count = sum(1 for c in conflicts if not c.blocking)
    can_prescribe = blocking_count == 0

    record_audit(
        db,
        action="CLINICAL_SAFETY_CHECK",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="OK" if can_prescribe else "BLOCK",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={
            "blocking": blocking_count,
            "warnings": warning_count,
            "med_count": len(medication_ids),
        },
        commit=False,
    )

    return SafetyCheckResponse(
        patient_id=patient_id,
        facility_id=facility_id,
        can_prescribe=can_prescribe,
        blocking_count=blocking_count,
        warning_count=warning_count,
        conflicts=conflicts,
        allergy_count_checked=base.allergy_count_checked,
        notes=notes + ["Clinical Safety Engine Phase 5 (allergy, DDI, duplicate, flags)"],
    )


def assert_clinical_safety_for_prescribe(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    medication_ids: list[UUID],
    encounter_id: UUID,
    override_reason: str | None,
    patient_is_pregnant: bool | None = None,
    actor_user_id: UUID | None = None,
) -> SafetyCheckResponse:
    result = run_clinical_safety_check(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        medication_ids=medication_ids,
        encounter_id=encounter_id,
        patient_is_pregnant=patient_is_pregnant,
        actor_user_id=actor_user_id,
    )
    critical = [c for c in result.conflicts if c.severity == "CRITICAL" and c.blocking]
    if critical:
        raise ValueError("CRITICAL_SAFETY_BLOCK")
    high_blocks = [c for c in result.conflicts if c.blocking and c.severity == "HIGH"]
    if high_blocks:
        reason = (override_reason or "").strip()
        if len(reason) < 15:
            raise ValueError("SAFETY_OVERRIDE_REQUIRED")
        record_audit(
            db,
            action="CLINICAL_SAFETY_OVERRIDE",
            resource_type="PERSON",
            resource_id=str(patient_id),
            result="OVERRIDE",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=patient_id,
            metadata={"reason_length": len(reason), "codes": [c.code for c in high_blocks]},
            commit=False,
        )
    return result
