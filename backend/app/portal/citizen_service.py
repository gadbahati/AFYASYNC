"""Afya Citizen — timeline, access history, charges, complaints, emergency summary."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.portal.citizen_schemas import (
    AccessHistoryItem,
    AccessHistoryResponse,
    ChargeExplainItem,
    ChargeExplainResponse,
    ComplaintCreate,
    ComplaintItem,
    ComplaintListResponse,
    DocumentItem,
    DocumentListResponse,
    EmergencySummary,
    TimelineEvent,
    TimelineResponse,
)
from app.portal.service import PortalError, get_my_profile
from app.patients.models import Person


def _get_person(db: Session, person_id: UUID) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise PortalError("PATIENT_NOT_FOUND")
    return person


def get_health_timeline(
    db: Session, person_id: UUID, *, limit: int = 50
) -> TimelineResponse:
    _get_person(db, person_id)
    limit = min(max(limit, 1), 100)
    events: list[TimelineEvent] = []

    # Encounters
    try:
        from app.encounters.models import Encounter

        for enc in db.scalars(
            select(Encounter)
            .where(Encounter.patient_id == person_id)
            .order_by(desc(Encounter.created_at))
            .limit(limit)
        ):
            events.append(
                TimelineEvent(
                    event_id=str(enc.id),
                    event_type="ENCOUNTER",
                    occurred_at=getattr(enc, "created_at", None),
                    title=f"Visit ({getattr(enc, 'encounter_type', 'encounter')})",
                    summary=getattr(enc, "status", None),
                    facility_id=getattr(enc, "facility_id", None),
                    resource_type="ENCOUNTER",
                    resource_id=str(enc.id),
                )
            )
    except Exception:
        pass

    # Diagnoses
    try:
        from app.clinical.models import Diagnosis

        for dx in db.scalars(
            select(Diagnosis)
            .where(Diagnosis.patient_id == person_id)
            .order_by(desc(Diagnosis.created_at))
            .limit(limit)
        ):
            events.append(
                TimelineEvent(
                    event_id=str(dx.id),
                    event_type="DIAGNOSIS",
                    occurred_at=getattr(dx, "created_at", None),
                    title=getattr(dx, "description", None) or getattr(dx, "code", "Diagnosis"),
                    summary=getattr(dx, "code", None),
                    facility_id=getattr(dx, "facility_id", None),
                    resource_type="DIAGNOSIS",
                    resource_id=str(dx.id),
                )
            )
    except Exception:
        pass

    # Allergies
    try:
        from app.clinical.models import Allergy

        for al in db.scalars(
            select(Allergy)
            .where(Allergy.patient_id == person_id)
            .order_by(desc(Allergy.created_at))
            .limit(20)
        ):
            events.append(
                TimelineEvent(
                    event_id=str(al.id),
                    event_type="ALLERGY",
                    occurred_at=getattr(al, "created_at", None),
                    title=f"Allergy: {getattr(al, 'substance', 'unknown')}",
                    summary=getattr(al, "severity", None),
                    resource_type="ALLERGY",
                    resource_id=str(al.id),
                )
            )
    except Exception:
        pass

    # Prescriptions
    try:
        from app.pharmacy.models import Prescription

        for rx in db.scalars(
            select(Prescription)
            .where(Prescription.patient_id == person_id)
            .order_by(desc(Prescription.created_at))
            .limit(limit)
        ):
            events.append(
                TimelineEvent(
                    event_id=str(rx.id),
                    event_type="MEDICATION",
                    occurred_at=getattr(rx, "created_at", None),
                    title=getattr(rx, "medication_name", None)
                    or getattr(rx, "drug_name", "Medication"),
                    summary=getattr(rx, "status", None),
                    facility_id=getattr(rx, "facility_id", None),
                    resource_type="PRESCRIPTION",
                    resource_id=str(rx.id),
                )
            )
    except Exception:
        pass

    # Lab orders
    try:
        from app.laboratory.models import LabOrder

        for lab in db.scalars(
            select(LabOrder)
            .where(LabOrder.patient_id == person_id)
            .order_by(desc(LabOrder.created_at))
            .limit(limit)
        ):
            events.append(
                TimelineEvent(
                    event_id=str(lab.id),
                    event_type="LABORATORY",
                    occurred_at=getattr(lab, "created_at", None),
                    title=f"Lab order {getattr(lab, 'order_id', lab.id)}",
                    summary=getattr(lab, "status", None),
                    facility_id=getattr(lab, "facility_id", None),
                    resource_type="LAB_ORDER",
                    resource_id=str(lab.id),
                )
            )
    except Exception:
        pass

    events.sort(key=lambda e: e.occurred_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    events = events[:limit]
    return TimelineResponse(person_id=person_id, events=events, total=len(events))


def get_access_history(
    db: Session, person_id: UUID, *, limit: int = 50
) -> AccessHistoryResponse:
    """Who accessed my record — from audit trail scoped to this patient."""
    _get_person(db, person_id)
    limit = min(max(limit, 1), 100)
    items: list[AccessHistoryItem] = []
    try:
        from app.audit.models import AuditLog

        rows = list(
            db.scalars(
                select(AuditLog)
                .where(AuditLog.patient_id == person_id)
                .order_by(desc(AuditLog.created_at))
                .limit(limit)
            )
        )
        for row in rows:
            meta = getattr(row, "metadata_json", None) or getattr(row, "metadata", None)
            meta_s = None
            if isinstance(meta, dict):
                # Never expose raw PHI dumps — only keys
                meta_s = ", ".join(sorted(meta.keys())[:8])
            items.append(
                AccessHistoryItem(
                    id=str(row.id),
                    action=getattr(row, "action", "") or "",
                    resource_type=getattr(row, "resource_type", None),
                    resource_id=getattr(row, "resource_id", None),
                    result=getattr(row, "result", None),
                    facility_id=getattr(row, "facility_id", None),
                    actor_user_id=getattr(row, "user_id", None),
                    created_at=getattr(row, "created_at", None),
                    metadata_summary=meta_s,
                )
            )
    except Exception:
        pass
    return AccessHistoryResponse(items=items, total=len(items))


def explain_my_charges(
    db: Session, person_id: UUID, *, limit: int = 50
) -> ChargeExplainResponse:
    _get_person(db, person_id)
    limit = min(max(limit, 1), 100)
    items: list[ChargeExplainItem] = []
    total_patient = Decimal("0.00")

    try:
        from app.billing.models import Invoice

        for inv in db.scalars(
            select(Invoice)
            .where(Invoice.patient_id == person_id)
            .order_by(desc(Invoice.created_at))
            .limit(limit)
        ):
            patient_amt = Decimal(str(getattr(inv, "patient_amount", 0) or 0))
            payer_amt = Decimal(str(getattr(inv, "payer_amount", 0) or 0))
            total = Decimal(str(getattr(inv, "total_amount", 0) or 0))
            total_patient += patient_amt
            explanation = (
                f"Invoice total {total}. Estimated payer share {payer_amt}, "
                f"your responsibility {patient_amt}. Status: {getattr(inv, 'status', 'UNKNOWN')}."
            )
            items.append(
                ChargeExplainItem(
                    charge_or_invoice_id=str(getattr(inv, "invoice_id", inv.id)),
                    kind="INVOICE",
                    description="Facility invoice",
                    amount=total,
                    patient_amount=patient_amt,
                    payer_amount=payer_amt,
                    status=getattr(inv, "status", None),
                    occurred_at=getattr(inv, "created_at", None),
                    explanation=explanation,
                )
            )
    except Exception:
        pass

    try:
        from app.billing.models import Charge

        for ch in db.scalars(
            select(Charge)
            .where(Charge.patient_id == person_id)
            .order_by(desc(Charge.created_at))
            .limit(limit)
        ):
            amt = Decimal(str(getattr(ch, "amount", 0) or getattr(ch, "total", 0) or 0))
            items.append(
                ChargeExplainItem(
                    charge_or_invoice_id=str(ch.id),
                    kind="CHARGE",
                    description=getattr(ch, "description", None) or "Service charge",
                    amount=amt,
                    patient_amount=None,
                    payer_amount=None,
                    status=getattr(ch, "status", None),
                    occurred_at=getattr(ch, "created_at", None),
                    explanation="Line charge recorded on your encounter. See linked invoice for payer split.",
                )
            )
    except Exception:
        pass

    return ChargeExplainResponse(items=items[:limit], total_patient_responsibility=total_patient)


def create_complaint(
    db: Session,
    *,
    person_id: UUID,
    payload: ComplaintCreate,
    actor_user_id: UUID,
):
    from app.portal.complaint_models import PatientComplaint

    _get_person(db, person_id)
    row = PatientComplaint(
        id=uuid4(),
        person_id=person_id,
        category=payload.category,
        subject=payload.subject.strip(),
        description=payload.description.strip(),
        related_encounter_id=payload.related_encounter_id,
        related_claim_ref=payload.related_claim_ref,
        status="OPEN",
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="PORTAL_COMPLAINT_CREATED",
        resource_type="COMPLAINT",
        resource_id=str(row.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person_id,
        metadata={"category": payload.category},
        commit=False,
    )
    return row


def list_complaints(db: Session, person_id: UUID) -> ComplaintListResponse:
    from app.portal.complaint_models import PatientComplaint

    rows = list(
        db.scalars(
            select(PatientComplaint)
            .where(PatientComplaint.person_id == person_id)
            .order_by(desc(PatientComplaint.created_at))
            .limit(50)
        )
    )
    return ComplaintListResponse(
        items=[
            ComplaintItem(
                id=r.id,
                category=r.category,
                subject=r.subject,
                status=r.status,
                created_at=r.created_at,
                resolution_note=r.resolution_note,
            )
            for r in rows
        ]
    )


def get_emergency_summary(db: Session, person_id: UUID) -> EmergencySummary:
    person, identity = get_my_profile(db, person_id)
    allergies: list[str] = []
    meds: list[str] = []
    conditions: list[str] = []

    try:
        from app.clinical.models import Allergy

        for al in db.scalars(
            select(Allergy).where(Allergy.patient_id == person_id).limit(20)
        ):
            allergies.append(str(getattr(al, "substance", "allergy")))
    except Exception:
        pass

    try:
        from app.pharmacy.models import Prescription

        for rx in db.scalars(
            select(Prescription)
            .where(
                Prescription.patient_id == person_id,
                Prescription.status.in_(["ACTIVE", "DISPENSED", "PRESCRIBED"]),
            )
            .limit(20)
        ):
            meds.append(
                str(
                    getattr(rx, "medication_name", None)
                    or getattr(rx, "drug_name", "medication")
                )
            )
    except Exception:
        pass

    try:
        from app.clinical.models import Diagnosis

        for dx in db.scalars(
            select(Diagnosis)
            .where(Diagnosis.patient_id == person_id)
            .order_by(desc(Diagnosis.created_at))
            .limit(10)
        ):
            conditions.append(
                str(getattr(dx, "description", None) or getattr(dx, "code", "condition"))
            )
    except Exception:
        pass

    return EmergencySummary(
        afya_id=identity.afya_id if identity else None,
        full_name=" ".join(
            x for x in [person.first_name, person.middle_name, person.last_name] if x
        ),
        date_of_birth=person.date_of_birth,
        sex=person.sex,
        allergies=allergies,
        active_medications=meds,
        critical_conditions=conditions,
        emergency_contact_name=person.emergency_contact_name,
        emergency_contact_phone=person.emergency_contact_phone,
        disclaimer=(
            "Emergency summary for care continuity only. "
            "Sensitive diagnoses respect consent rules at the clinical system; "
            "this view is limited to the patient account holder."
        ),
    )


def list_my_documents(db: Session, person_id: UUID) -> DocumentListResponse:
    items: list[DocumentItem] = []
    try:
        from app.continuity.models import ContinuityCard

        for card in db.scalars(
            select(ContinuityCard)
            .where(ContinuityCard.person_id == person_id)
            .order_by(desc(ContinuityCard.created_at))
            .limit(20)
        ):
            items.append(
                DocumentItem(
                    id=str(card.id),
                    doc_type="CONTINUITY_CARD",
                    title="Continuity / wallet card",
                    created_at=getattr(card, "created_at", None),
                    status=getattr(card, "status", None),
                )
            )
    except Exception:
        pass
    return DocumentListResponse(items=items)
