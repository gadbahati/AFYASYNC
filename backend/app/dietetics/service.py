from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.patients.models import PatientFacility
from app.dietetics.models import DietOrder, NutritionAssessment


def _patient_active(db: Session, patient_id: UUID, facility_id: UUID) -> bool:
    return db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    ) is not None


def _validate_encounter(db: Session, patient_id: UUID, encounter_id: UUID | None, facility_id: UUID) -> None:
    if encounter_id is None:
        return
    encounter = db.scalar(
        select(Encounter).where(
            Encounter.id == encounter_id,
            Encounter.patient_id == patient_id,
            Encounter.facility_id == facility_id,
        )
    )
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if getattr(encounter, "status", None) not in {"OPEN", "IN_PROGRESS"}:
        raise ValueError("ENCOUNTER_NOT_OPEN")


def _bmi_from_measurements(weight: str | None, height: str | None) -> float | None:
    try:
        kg = float(weight) if weight is not None else None
        cm = float(height) if height is not None else None
        if kg is None or cm is None or kg <= 0 or cm <= 0:
            return None
        meters = cm / 100
        return round(kg / (meters * meters), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def assess_nutrition(db: Session, facility_id: UUID, actor: UUID, payload):
    if not _patient_active(db, payload.patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    _validate_encounter(db, payload.patient_id, payload.encounter_id, facility_id)

    values = payload.model_dump()
    if values.get("bmi") is None:
        values["bmi"] = _bmi_from_measurements(values.get("weight"), values.get("height"))

    item = NutritionAssessment(facility_id=facility_id, assessed_by=actor, **values)
    db.add(item)
    record_audit(
        db,
        action="NUTRITION_ASSESSED",
        resource_type="NutritionAssessment",
        result="SUCCESS",
        user_id=actor,
        resource_id=str(item.id),
        facility_id=facility_id,
        patient_id=payload.patient_id,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item


def order_diet(db: Session, facility_id: UUID, actor: UUID, payload):
    if not _patient_active(db, payload.patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    _validate_encounter(db, payload.patient_id, payload.encounter_id, facility_id)

    item = DietOrder(facility_id=facility_id, ordered_by=actor, **payload.model_dump())
    db.add(item)
    record_audit(
        db,
        action="DIET_ORDER_CREATED",
        resource_type="DietOrder",
        result="SUCCESS",
        user_id=actor,
        resource_id=str(item.id),
        facility_id=facility_id,
        patient_id=payload.patient_id,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item


def list_patient_diet_orders(db: Session, facility_id: UUID, patient_id: UUID):
    if not _patient_active(db, patient_id, facility_id):
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    return list(
        db.scalars(
            select(DietOrder)
            .where(DietOrder.facility_id == facility_id, DietOrder.patient_id == patient_id)
            .order_by(DietOrder.ordered_at.desc())
        ).all()
    )


def update_diet_order_status(db: Session, facility_id: UUID, actor: UUID, order_id: UUID, status_value: str):
    item = db.scalar(
        select(DietOrder).where(DietOrder.id == order_id, DietOrder.facility_id == facility_id)
    )
    if item is None:
        raise ValueError("DIET_ORDER_NOT_FOUND")
    item.status = status_value
    record_audit(
        db,
        action="DIET_ORDER_STATUS_UPDATED",
        resource_type="DietOrder",
        result="SUCCESS",
        user_id=actor,
        resource_id=str(item.id),
        facility_id=facility_id,
        patient_id=item.patient_id,
        commit=False,
    )
    db.commit()
    db.refresh(item)
    return item
