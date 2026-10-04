"""Phase 137–153 — printable clinical encounter summary.

Imaging, lab, and pharmacy dispense extraction from fulfilled orders.
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


def _parse_pharmacy_dispense(o: ClinicalOrder) -> dict:
    """Phase 153 — extract Dispensed / Batch from order notes."""
    qty = batch = None
    notes = o.notes or ""
    for line in str(notes).splitlines():
        sline = line.strip()
        low = sline.lower()
        if low.startswith("dispensed:"):
            rest = sline.split(":", 1)[1].strip()
            if "·" in rest or "batch:" in low:
                parts = rest.replace("·", "|").split("|")
                qty = parts[0].strip()
                for p in parts[1:]:
                    if "batch" in p.lower():
                        batch = p.split(":", 1)[-1].strip()
            else:
                qty = rest
        elif low.startswith("batch:"):
            batch = sline.split(":", 1)[1].strip()
    return {
        "order_id": str(o.id),
        "code": o.code,
        "description": o.description,
        "status": o.status,
        "dispense_qty": qty,
        "batch_no": batch,
        "notes": o.notes,
    }


def _parse_lab_result(o: ClinicalOrder) -> dict:
    value = units = flag = None
    notes = o.notes or ""
    for line in str(notes).splitlines():
        sline = line.strip()
        if sline.lower().startswith("result:"):
            rest = sline.split(":", 1)[1].strip()
            if "(" in rest and rest.endswith(")"):
                main, fl = rest.rsplit("(", 1)
                flag = fl.rstrip(")").strip()
                rest = main.strip()
            parts = rest.split()
            if parts:
                value = parts[0]
                if len(parts) > 1:
                    units = " ".join(parts[1:])
    return {
        "order_id": str(o.id),
        "code": o.code,
        "description": o.description,
        "status": o.status,
        "value": value,
        "units": units,
        "flag": flag,
        "notes": o.notes,
    }


def _parse_imaging_report(notes: str | None) -> dict:
    modality = None
    impression = None
    if not notes:
        return {"modality": None, "impression": None, "raw_notes": None}
    for line in str(notes).splitlines():
        s = line.strip()
        if s.lower().startswith("modality:"):
            modality = s.split(":", 1)[1].strip() or modality
        elif s.lower().startswith("impression:"):
            impression = s.split(":", 1)[1].strip() or impression
    return {"modality": modality, "impression": impression, "raw_notes": notes}


def build_encounter_summary(
    db: Session,
    *,
    encounter_id: UUID,
    facility_id: UUID,
) -> dict:
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
        if val is None:
            return []
        if isinstance(val, list):
            return [_serialize_one(x) or {} for x in val]
        return [_serialize_one(val) or {}]

    clinical_orders = list(
        db.scalars(
            select(ClinicalOrder)
            .where(ClinicalOrder.encounter_id == encounter_id)
            .order_by(ClinicalOrder.created_at.asc())
        )
    )

    discharge = db.scalar(
        select(ClinicalDischarge).where(ClinicalDischarge.encounter_id == encounter_id)
    )

    order_payload = []
    imaging_reports = []
    lab_results = []
    pharmacy_dispenses = []
    for o in clinical_orders:
        item = {
            "id": str(o.id),
            "order_type": o.order_type,
            "code": o.code,
            "description": o.description,
            "priority": o.priority,
            "status": o.status,
            "notes": o.notes,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        order_payload.append(item)
        ot = (o.order_type or "").upper()
        if ot in {"IMAGING", "RADIOLOGY"} and o.status == "COMPLETED":
            parsed = _parse_imaging_report(o.notes)
            imaging_reports.append(
                {
                    "order_id": str(o.id),
                    "code": o.code,
                    "description": o.description,
                    "status": o.status,
                    "modality": parsed["modality"],
                    "impression": parsed["impression"],
                    "notes": o.notes,
                }
            )
        if ot in {"LAB", "LABORATORY"} and o.status == "COMPLETED":
            lab_results.append(_parse_lab_result(o))
        if ot in {"PHARMACY", "RX"} and o.status == "COMPLETED":
            pharmacy_dispenses.append(_parse_pharmacy_dispense(o))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "facility": {
            "id": str(facility_id),
            "name": getattr(facility, "name", None) if facility else None,
            "code": getattr(facility, "code", None) if facility else None,
        },
        "patient": {
            "id": str(enc.patient_id),
            "display_name": (
                getattr(patient, "display_name", None)
                or getattr(patient, "full_name", None)
                if patient
                else None
            ),
            "identifier": getattr(patient, "national_id", None) if patient else None,
        },
        "encounter": {
            "id": str(enc.id),
            "status": getattr(enc, "status", None),
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
        "clinical_orders": order_payload,
        "imaging_reports": imaging_reports,
        "lab_results": lab_results,
        "pharmacy_dispenses": pharmacy_dispenses,
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
        "developer": "BAHATI GAD WANGWE",
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
