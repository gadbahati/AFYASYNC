"""Phase 137 — printable clinical encounter summary.

Developed by BAHATI GAD WANGWE.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clinical.discharge_models import ClinicalDischarge
from app.clinical.order_models import ClinicalOrder
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import Person


class SummaryError(ValueError):
    pass


def build_encounter_summary(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
) -> dict:
    """Aggregate encounter clinical data into a print-ready summary payload."""
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise SummaryError("ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise SummaryError("FACILITY_ACCESS_DENIED")

    facility = db.get(Facility, facility_id)
    patient = db.get(Person, enc.patient_id)

    timeline: dict = {}
    try:
        from app.clinical.service import get_encounter_clinical_summary

        try:
            raw = get_encounter_clinical_summary(db, encounter_id, facility_id)
        except TypeError:
            raw = get_encounter_clinical_summary(db, encounter_id)
        if isinstance(raw, dict):
            timeline = raw
    except Exception:
        timeline = {}

    def _rows(key: str):
        val = timeline.get(key) if isinstance(timeline, dict) else None
        if not isinstance(val, list):
            return []
        out = []
        for item in val:
            if hasattr(item, "__dict__") and not isinstance(item, dict):
                d = {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
                out.append(_jsonable(d))
            elif isinstance(item, dict):
                out.append(_jsonable(item))
            else:
                out.append(str(item))
        return out

    clinical_orders = list(
        db.scalars(
            select(ClinicalOrder)
            .where(ClinicalOrder.encounter_id == encounter_id)
            .order_by(ClinicalOrder.created_at.asc())
        )
    )
    discharge = db.scalar(select(ClinicalDischarge).where(ClinicalDischarge.encounter_id == encounter_id))

    patient_name = None
    if patient is not None:
        parts = [
            getattr(patient, "first_name", None),
            getattr(patient, "middle_name", None),
            getattr(patient, "last_name", None),
        ]
        patient_name = " ".join(p for p in parts if p) or getattr(patient, "full_name", None)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
        "facility": {
            "id": str(facility_id),
            "name": getattr(facility, "name", None) if facility else None,
            "code": getattr(facility, "code", None) if facility else None,
        },
        "patient": {
            "id": str(enc.patient_id),
            "name": patient_name,
            "afya_id": getattr(patient, "afya_id", None) if patient else None,
            "national_id": getattr(patient, "national_id_number", None) if patient else None,
        },
        "encounter": {
            "id": str(enc.id),
            "encounter_id": getattr(enc, "encounter_id", None),
            "type": getattr(enc, "encounter_type", None),
            "status": enc.status,
            "started_at": enc.started_at.isoformat() if getattr(enc, "started_at", None) else None,
            "ended_at": enc.ended_at.isoformat() if getattr(enc, "ended_at", None) else None,
            "coverage_mode": getattr(enc, "coverage_mode", None),
        },
        "vitals": _rows("vitals"),
        "consultation": _serialize_one(timeline.get("consultation") if isinstance(timeline, dict) else None),
        "diagnoses": _rows("diagnoses"),
        "procedures": _rows("procedures"),
        "clinical_notes": _rows("clinical_notes"),
        "lab_orders_legacy": _rows("lab_orders"),
        "prescriptions_legacy": _rows("prescriptions"),
        "clinical_orders": [
            {
                "id": str(o.id),
                "order_type": o.order_type,
                "code": o.code,
                "description": o.description,
                "priority": o.priority,
                "status": o.status,
                "notes": o.notes,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in clinical_orders
        ],
        "discharge": (
            {
                "disposition": discharge.disposition,
                "outcome": discharge.outcome,
                "follow_up_instructions": discharge.follow_up_instructions,
                "follow_up_date": discharge.follow_up_date.isoformat()
                if discharge.follow_up_date
                else None,
                "discharge_summary": discharge.discharge_summary,
                "discharged_at": discharge.discharged_at.isoformat()
                if discharge.discharged_at
                else None,
            }
            if discharge
            else None
        ),
    }


def _jsonable(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, UUID):
            out[k] = str(v)
        else:
            out[k] = v
    return out


def _serialize_one(obj) -> dict | None:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return _jsonable(obj)
    if hasattr(obj, "__dict__"):
        return _jsonable({k: v for k, v in obj.__dict__.items() if not k.startswith("_")})
    return None
