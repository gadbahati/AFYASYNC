from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.patients.record_service import get_patient_record_summary
from app.rbac.models import User


class PatientTimelineEvent(BaseModel):
    id: str
    type: str
    occurred_at: datetime
    title: str
    status: str | None = None
    encounter_id: str | None = None
    source_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PatientTimelineResponse(BaseModel):
    patient_id: UUID
    items: list[PatientTimelineEvent]
    total: int
    limit: int
    offset: int


router = APIRouter(prefix="/api/v1/patients", tags=["Patient Timeline"])


def _event(event_id: str, kind: str, occurred_at: datetime | None, title: str, status_value: str | None = None, encounter_id: str | None = None, source_id: str | None = None, metadata: dict[str, Any] | None = None) -> PatientTimelineEvent | None:
    if occurred_at is None:
        return None
    return PatientTimelineEvent(id=event_id, type=kind, occurred_at=occurred_at, title=title, status=status_value, encounter_id=encounter_id, source_id=source_id, metadata=metadata or {})


def _build_events(record: dict[str, Any]) -> list[PatientTimelineEvent]:
    events: list[PatientTimelineEvent] = []
    for encounter in record.get("encounters", []):
        eid = str(encounter["id"])
        event = _event(f"encounter:{eid}", "ENCOUNTER", encounter.get("started_at"), f"Encounter {encounter.get('encounter_id') or eid}", encounter.get("status"), eid, eid, {"department": encounter.get("department_name"), "type": encounter.get("type"), "reason": encounter.get("reason")})
        if event: events.append(event)
        consultation = encounter.get("consultation")
        if consultation:
            event = _event(f"consultation:{consultation['id']}", "CONSULTATION", consultation.get("updated_at") or consultation.get("created_at"), "Clinical consultation recorded", None, eid, str(consultation["id"]), {"chief_complaint": consultation.get("chief_complaint"), "assessment": consultation.get("assessment")})
            if event: events.append(event)
        for vital in encounter.get("vitals", []):
            event = _event(f"vitals:{vital['id']}", "VITALS", vital.get("recorded_at"), "Vital signs recorded", None, eid, str(vital["id"]), {"blood_pressure": f"{vital.get('systolic_bp')}/{vital.get('diastolic_bp')}", "pulse": vital.get("pulse"), "temperature_c": vital.get("temperature_c"), "oxygen_saturation": vital.get("oxygen_saturation")})
            if event: events.append(event)
        for diagnosis in encounter.get("diagnoses", []):
            event = _event(f"diagnosis:{diagnosis['id']}", "DIAGNOSIS", diagnosis.get("created_at"), diagnosis.get("diagnosis_name") or "Diagnosis recorded", diagnosis.get("status"), eid, str(diagnosis["id"]), {"code": diagnosis.get("diagnosis_code"), "type": diagnosis.get("diagnosis_type")})
            if event: events.append(event)
    for plan in record.get("care_plans", []):
        event = _event(f"care-plan:{plan['id']}", "CARE_PLAN", plan.get("updated_at") or plan.get("created_at"), plan.get("title") or "Care plan", plan.get("status"), plan.get("encounter_id"), str(plan["id"]), {"goals": plan.get("goals"), "target_date": plan.get("target_date")})
        if event: events.append(event)
    for order in record.get("laboratory", []):
        oid = str(order["id"])
        event = _event(f"lab-order:{oid}", "LAB_ORDER", order.get("created_at"), f"Laboratory order {order.get('order_id') or oid}", order.get("status"), order.get("encounter_id"), oid, {"tests": len(order.get("items", [])), "priority": order.get("priority")})
        if event: events.append(event)
        for item in order.get("items", []):
            result = item.get("result")
            if result:
                rid = str(result["id"])
                event = _event(f"lab-result:{rid}", "LAB_RESULT", result.get("verified_at") or result.get("created_at"), f"Laboratory result: {item.get('name') or item.get('code')}", result.get("status"), order.get("encounter_id"), rid, {"result": result.get("result"), "unit": result.get("unit"), "reference_range": result.get("reference_range")})
                if event: events.append(event)
    for prescription in record.get("prescriptions", []):
        pid = str(prescription["id"])
        event = _event(f"prescription:{pid}", "PRESCRIPTION", prescription.get("created_at"), f"Prescription {prescription.get('prescription_id') or pid}", prescription.get("status"), prescription.get("encounter_id"), pid, {"items": len(prescription.get("items", []))})
        if event: events.append(event)
    for action in record.get("medication_actions", []):
        aid = str(action["id"])
        event = _event(f"medication-action:{aid}", "MEDICATION_ACTION", action.get("performed_at"), f"Medication {action.get('action_type', 'action').replace('_', ' ').lower()}: {action.get('medication_name') or 'medication'}", None, action.get("encounter_id"), aid, {"quantity": action.get("quantity"), "action_type": action.get("action_type")})
        if event: events.append(event)
    for admission in record.get("admissions", []):
        aid = str(admission["id"])
        event = _event(f"admission:{aid}", "ADMISSION", admission.get("admitted_at"), f"Admission {admission.get('admission_number') or aid}", admission.get("status"), admission.get("encounter_id"), aid, {"ward": admission.get("ward"), "bed": admission.get("bed"), "diagnosis": admission.get("diagnosis")})
        if event: events.append(event)
        discharge = _event(f"discharge:{aid}", "DISCHARGE", admission.get("discharged_at"), "Patient discharged", admission.get("status"), admission.get("encounter_id"), aid, {"ward": admission.get("ward"), "bed": admission.get("bed")})
        if discharge: events.append(discharge)
    for auth in record.get("preauthorizations", []):
        aid = str(auth["id"])
        event = _event(f"preauthorization:{aid}", "PREAUTHORIZATION", auth.get("requested_at"), f"Preauthorization {auth.get('authorization_number') or aid}", auth.get("status"), auth.get("encounter_id"), aid, {"payer": auth.get("payer_name"), "requested_amount": auth.get("requested_amount"), "approved_amount": auth.get("approved_amount")})
        if event: events.append(event)
        decided = _event(f"preauthorization-decision:{aid}", "PREAUTHORIZATION_DECISION", auth.get("decided_at"), "Preauthorization decision", auth.get("status"), auth.get("encounter_id"), aid, {"approved_amount": auth.get("approved_amount"), "external_reference": auth.get("external_reference")})
        if decided: events.append(decided)
    for appointment in record.get("appointments", []):
        aid = str(appointment["id"])
        event = _event(f"appointment:{aid}", "APPOINTMENT", appointment.get("appointment_at"), "Appointment", appointment.get("status"), appointment.get("encounter_id"), aid, {})
        if event: events.append(event)
    for queue in record.get("queue_history", []):
        qid = str(queue.get("id"))
        event = _event(f"queue:{qid}", "QUEUE", queue.get("queued_at"), "Patient entered care queue", queue.get("status"), queue.get("encounter_id"), qid, {"queue": queue.get("queue_name")})
        if event: events.append(event)
    for referral in record.get("referrals", []):
        rid = str(referral["id"])
        event = _event(f"referral:{rid}", "REFERRAL", referral.get("created_at"), "Referral created", referral.get("status"), referral.get("encounter_id"), rid, {"reason": referral.get("reason"), "destination": referral.get("destination_facility_name")})
        if event: events.append(event)
    for transfer in record.get("transfers", []):
        tid = str(transfer["id"])
        event = _event(f"transfer:{tid}", "TRANSFER", transfer.get("created_at"), "Patient transfer created", transfer.get("status"), transfer.get("encounter_id"), tid, {"reason": transfer.get("reason"), "destination": transfer.get("destination_facility_name")})
        if event: events.append(event)
    events.sort(key=lambda item: item.occurred_at, reverse=True)
    return events


@router.get("/{patient_id}/timeline", response_model=PatientTimelineResponse)
def patient_timeline(patient_id: UUID, limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0), user: User = Depends(require_permission("patients.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientTimelineResponse:
    try:
        record = get_patient_record_summary(db, patient_id, facility_id)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "PATIENT_TIMELINE_UNAVAILABLE", "message": "Patient timeline is temporarily unavailable."})
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found at this facility."})
    events = _build_events(record)
    page = events[offset:offset + limit]
    record_audit(db, action="VIEW_PATIENT_TIMELINE", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"total": len(events), "limit": limit, "offset": offset}, commit=True)
    return PatientTimelineResponse(patient_id=patient_id, items=page, total=len(events), limit=limit, offset=offset)
