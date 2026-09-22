"""Prescribe-time allergy, interaction, and duplicate therapy checks."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clinical.models import Allergy
from app.encounters.models import Encounter
from app.pharmacy.models import Medication, Prescription, PrescriptionItem
from app.pharmacy.safety_schemas import SafetyCheckRequest, SafetyCheckResponse, SafetyConflict

# High-risk pairs by generic/name tokens (casefold). Conservative starter set.
# Expand via admin catalogue later — never silent-fail clinical risk.
_INTERACTION_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("warfarin", "aspirin", "Increased bleeding risk"),
    ("warfarin", "ibuprofen", "Increased bleeding risk"),
    ("methotrexate", "trimethoprim", "Severe toxicity risk"),
    ("simvastatin", "clarithromycin", "Myopathy / rhabdomyolysis risk"),
    ("sildenafil", "isosorbide", "Severe hypotension risk"),
    ("sildenafil", "nitroglycerin", "Severe hypotension risk"),
    ("monoamine", "ssri", "Serotonin syndrome risk"),
    ("phenelzine", "fluoxetine", "Serotonin syndrome risk"),
)

_SEVERE = {"SEVERE", "LIFE_THREATENING"}
_CRITICAL_ALLERGY = {"LIFE_THREATENING"}


def _tokens(*values: str | None) -> set[str]:
    out: set[str] = set()
    for v in values:
        if not v:
            continue
        t = v.strip().casefold()
        if t:
            out.add(t)
            for part in t.replace("/", " ").replace("-", " ").split():
                if len(part) >= 3:
                    out.add(part)
    return out


def _med_tokens(med: Medication) -> set[str]:
    return _tokens(med.name, med.generic_name, med.code)


def _allergy_match(allergen: str, med_tokens: set[str]) -> bool:
    a = allergen.strip().casefold()
    if not a:
        return False
    if a in med_tokens:
        return True
    for t in med_tokens:
        if a in t or t in a:
            return True
    return False


def load_active_allergies(db: Session, patient_id: UUID) -> list[Allergy]:
    """Cross-facility active allergies for the patient (safety > silo)."""
    return list(
        db.scalars(
            select(Allergy).where(
                Allergy.patient_id == patient_id,
                Allergy.status == "ACTIVE",
            )
        )
    )


def check_prescription_safety(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    medication_ids: list[UUID],
    encounter_id: UUID | None = None,
) -> SafetyCheckResponse:
    conflicts: list[SafetyConflict] = []
    notes: list[str] = [
        "Allergy scan includes all ACTIVE allergies for this patient across facilities.",
        "Interaction list is a conservative starter set — expand via formulary rules.",
    ]

    if encounter_id is not None:
        enc = db.get(Encounter, encounter_id)
        if enc is None:
            raise ValueError("ENCOUNTER_NOT_FOUND")
        if enc.facility_id != facility_id:
            raise ValueError("FACILITY_ACCESS_DENIED")
        if enc.patient_id != patient_id:
            raise ValueError("PATIENT_ENCOUNTER_MISMATCH")

    meds: list[Medication] = []
    seen: set[UUID] = set()
    for mid in medication_ids:
        if mid in seen:
            conflicts.append(
                SafetyConflict(
                    code="DUPLICATE_LINE",
                    severity="MEDIUM",
                    title="Duplicate medication on same order",
                    detail="Same medication appears more than once on this prescription",
                    medication_id=mid,
                    blocking=False,
                )
            )
            continue
        seen.add(mid)
        med = db.get(Medication, mid)
        if med is None or med.status != "ACTIVE":
            raise ValueError("MEDICATION_NOT_FOUND")
        meds.append(med)

    allergies = load_active_allergies(db, patient_id)

    # --- Allergy conflicts ---
    for med in meds:
        tokens = _med_tokens(med)
        for allergy in allergies:
            if not _allergy_match(allergy.allergen, tokens):
                continue
            sev = (allergy.severity or "UNKNOWN").upper()
            if sev in _CRITICAL_ALLERGY:
                severity, blocking = "CRITICAL", True
            elif sev in _SEVERE:
                severity, blocking = "HIGH", True
            elif sev == "MODERATE":
                severity, blocking = "MEDIUM", False
            else:
                severity, blocking = "LOW", False
            conflicts.append(
                SafetyConflict(
                    code="ALLERGY_MATCH",
                    severity=severity,
                    title=f"Allergy match: {allergy.allergen}",
                    detail=(
                        f"Medication '{med.name}' may conflict with documented allergen "
                        f"'{allergy.allergen}' (severity={sev})"
                        + (f"; reaction: {allergy.reaction}" if allergy.reaction else "")
                    ),
                    medication_id=med.id,
                    medication_name=med.name,
                    allergen=allergy.allergen,
                    allergy_id=allergy.id,
                    blocking=blocking,
                )
            )

    # --- Drug–drug interactions among ordered meds ---
    for i, a in enumerate(meds):
        ta = _med_tokens(a)
        for b in meds[i + 1 :]:
            tb = _med_tokens(b)
            for x, y, msg in _INTERACTION_PAIRS:
                if (x in ta and y in tb) or (y in ta and x in tb):
                    conflicts.append(
                        SafetyConflict(
                            code="DRUG_INTERACTION",
                            severity="HIGH",
                            title="Potential drug–drug interaction",
                            detail=f"{a.name} + {b.name}: {msg}",
                            medication_id=a.id,
                            medication_name=a.name,
                            interacting_medication_id=b.id,
                            blocking=True,
                        )
                    )

    # --- Duplicate therapy vs active prescriptions ---
    active_rx = list(
        db.scalars(
            select(Prescription).where(
                Prescription.patient_id == patient_id,
                Prescription.status.in_(["ACTIVE", "PENDING", "PRESCRIBED"]),
            )
        )
    )
    if active_rx:
        existing_items = list(
            db.scalars(
                select(PrescriptionItem).where(
                    PrescriptionItem.prescription_id.in_([r.id for r in active_rx])
                )
            )
        )
        existing_med_ids = {item.medication_id for item in existing_items}
        for med in meds:
            if med.id in existing_med_ids:
                conflicts.append(
                    SafetyConflict(
                        code="DUPLICATE_THERAPY",
                        severity="MEDIUM",
                        title="Possible duplicate therapy",
                        detail=f"'{med.name}' already appears on an active prescription",
                        medication_id=med.id,
                        medication_name=med.name,
                        blocking=False,
                    )
                )

    blocking_count = sum(1 for c in conflicts if c.blocking)
    warning_count = len(conflicts) - blocking_count
    can_prescribe = blocking_count == 0

    return SafetyCheckResponse(
        patient_id=patient_id,
        facility_id=facility_id,
        can_prescribe=can_prescribe,
        blocking_count=blocking_count,
        warning_count=warning_count,
        conflicts=conflicts,
        allergy_count_checked=len(allergies),
        notes=notes,
    )


def assert_can_create_prescription(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    medication_ids: list[UUID],
    encounter_id: UUID,
    allergy_override_reason: str | None,
    patient_is_pregnant: bool | None = None,
    actor_user_id: UUID | None = None,
) -> SafetyCheckResponse:
    """National Phase 5 — prescribe-time intercept via Clinical Safety Engine."""
    from app.clinical_safety.engine import assert_clinical_safety_for_prescribe

    return assert_clinical_safety_for_prescribe(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        medication_ids=medication_ids,
        encounter_id=encounter_id,
        override_reason=allergy_override_reason,
        patient_is_pregnant=patient_is_pregnant,
        actor_user_id=actor_user_id,
    )
