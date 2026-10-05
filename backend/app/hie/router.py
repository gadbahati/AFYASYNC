"""HIE depth APIs — robust national exchange."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.hie.delivery_service import deliver_job, list_jobs, queue_bundle
from app.hie.consent_service import create_consent, list_consents, revoke_consent
from app.hie.service import (
    build_patient_summary_bundle,
    build_referral_package,
    capability_statement,
    list_export_logs,
    list_nodes,
    upsert_node,
    validate_inbound_bundle,
    resolve_inbound_patient,
    import_inbound_clinical_resources,
    list_imported_patient_resources,
)
from app.rbac.models import User
from app.hie.provider_identity import provider_identity_resources

router = APIRouter(prefix="/api/v1/hie", tags=["HIE"])


class ReferralBody(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    clinical_summary: str | None = Field(default=None, max_length=4000)
    destination: str | None = Field(default=None, max_length=200)
    destination_node_id: UUID | None = None
    purpose_of_use: str = Field(default="TREATMENT", max_length=40)


class InboundBody(BaseModel):
    bundle: dict
    source_code: str | None = Field(default=None, max_length=80)
    source_node_id: UUID | None = None


class NodeUpsert(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=200)
    node_type: str = Field(default="FACILITY", max_length=40)
    endpoint_url: str | None = Field(default=None, max_length=500)
    facility_id: UUID | None = None
    trust_level: str = Field(default="STANDARD", max_length=20)


@router.get("/providers/{staff_id}/identity")
def provider_identity(\n    staff_id: UUID,\n    db: Session = Depends(get_db),\n    facility_id: UUID = Depends(get_facility_context),\n    user: User = Depends(require_permission("staff.read")),\n):\n    _ = user\n    try:\n        resources = provider_identity_resources(db, facility_id=facility_id, staff_id=staff_id)\n        return {"staff_id": str(staff_id), "resources": resources}\n    except ValueError as exc:\n        code = str(exc)\n        raise HTTPException(status_code=404 if "NOT_FOUND" in code else 400, detail=code) from exc\n\n\n@router.get("/metadata")
def hie_metadata():
    return capability_statement()


@router.get("/Patient/{patient_id}/$summary")
def patient_summary(
    patient_id: UUID,
    purpose: str | None = Query(default="care-coordination", max_length=200),
    purpose_of_use: str = Query(default="TREATMENT", max_length=40),
    destination: str | None = Query(default=None, max_length=200),
    destination_node_id: UUID | None = Query(default=None),
    include_labs: bool = Query(default=True),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        bundle = build_patient_summary_bundle(
            db,
            patient_id=patient_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            purpose=purpose,
            purpose_of_use=purpose_of_use,
            destination=destination,
            destination_node_id=destination_node_id,
            include_labs=include_labs,
        )
        db.commit()
        return bundle
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code or "FACILITY" in code else 400,
            detail=code,
        ) from exc


@router.post("/referral-package")
def referral_package(
    body: ReferralBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        bundle = build_referral_package(
            db,
            patient_id=body.patient_id,
            facility_id=facility_id,
            encounter_id=body.encounter_id,
            clinical_summary=body.clinical_summary,
            actor_user_id=user.id,
            destination=body.destination,
            destination_node_id=body.destination_node_id,
            purpose_of_use=body.purpose_of_use,
        )
        db.commit()
        return bundle
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code or "FACILITY" in code else 400,
            detail=code,
        ) from exc


@router.post("/inbound")
def inbound_document(
    body: InboundBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        result = validate_inbound_bundle(
            db,
            facility_id=facility_id,
            payload=body.bundle,
            source_code=body.source_code,
            source_node_id=body.source_node_id,
            actor_user_id=user.id,
        )
        if result["validation_status"] == "ACCEPTED":
            result["mpi"] = resolve_inbound_patient(
                db,
                inbound_id=UUID(result["id"]),
                facility_id=facility_id,
                actor_user_id=user.id,
            )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/inbound")
def inbound_documents(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = user
    from sqlalchemy import select
    from app.hie.models import HieInboundDocument
    rows = list(
        db.scalars(
            select(HieInboundDocument)
            .where(HieInboundDocument.facility_id == facility_id)
            .order_by(HieInboundDocument.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": str(row.id),
            "patient_id": str(row.patient_id) if row.patient_id else None,
            "source_node_id": str(row.source_node_id) if row.source_node_id else None,
            "source_code": row.source_code,
            "bundle_id": row.bundle_id,
            "document_type": row.document_type,
            "resource_count": row.resource_count,
            "validation_status": row.validation_status,
            "match_status": row.match_status,
            "match_reasons": row.match_reasons or [],
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.post("/inbound/{inbound_id}/resolve")
def resolve_inbound(
    inbound_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        result = resolve_inbound_patient(
            db,
            inbound_id=inbound_id,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code else 409 if "ACCEPTED" in code else 400,
            detail=code,
        ) from exc


@router.put("/nodes")
def put_node(
    body: NodeUpsert,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = facility_id, user
    try:
        row = upsert_node(db, data=body.model_dump())
        db.commit()
        return {
            "id": str(row.id),
            "code": row.code,
            "name": row.name,
            "node_type": row.node_type,
            "status": row.status,
            "trust_level": row.trust_level,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/nodes")
def get_nodes(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = facility_id, user
    return [
        {
            "id": str(n.id),
            "code": n.code,
            "name": n.name,
            "node_type": n.node_type,
            "endpoint_url": n.endpoint_url,
            "trust_level": n.trust_level,
            "status": n.status,
        }
        for n in list_nodes(db)
    ]


@router.post("/consents")
def grant_hie_consent(
    patient_id: UUID,
    purpose: str = Query(default="HOPERAT"),
    recipient_node_id: UUID | None = None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.write")),
):
    try:
        c=create_consent(db,patient_id=patient_id,facility_id=facility_id,recipient_node_id=recipient_node_id,purpose=purpose,period_start=period_start,period_end=period_end,created_by=user.id)
        db.commit()
        return {"id":str(c.id),"patient_id":str(c.patient_id),"recipient_node_id":str(c.recipient_node_id) if c.recipient_node_id else None,"status":c.status,"decision":c.decision,"purpose":c.purpose,"fhir_resource":c.fhir_resource}
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc

@router.post("/consents/{consent_id}/revoke")
def revoke_hie_consent(
    consent_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.write")),
):
    try:
        c=revoke_consent(db,consent_id=consent_id,facility_id=facility_id,actor_user_id=user.id)
        db.commit()
        return {"id":str(c.id),"status":c.status,"revoked_at":c.revoked_at.isoformat() if c.revoked_at else None}
    except ValueError as exc:
        raise HTTPException(status_code=404,detail=str(exc)) from exc

@router.get("/consents")
def get_hie_consents(
    patient_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _=user
    return [{"id":str(c.id),"patient_id":str(c.patient_id),"recipient_node_id":str(c.recipient_node_id) if c.recipient_node_id else None,"status":c.status,"decision":c.decision,"purpose":c.purpose,"scope":c.scope,"period_start":c.period_start.isoformat() if c.period_start else None,"period_end":c.period_end.isoformat() if c.period_end else None,"fhir_resource":c.fhir_resource} for c in list_consents(db,patient_id=patient_id,facility_id=facility_id)]

@router.post("/deliver")
def queue_delivery(patient_id: UUID, destination_node_id: UUID, bundle: dict, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission("patients.record.write"))):
    try:
        job = queue_bundle(db, facility_id=facility_id, patient_id=patient_id, destination_node_id=destination_node_id, payload=bundle, created_by=user.id)
        db.commit()
        return {"id": str(job.id), "status": job.status, "idempotency_key": job.idempotency_key, "destination_node_id": str(job.destination_node_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/deliver/{job_id}")
def deliver_queued_job(job_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission("patients.record.write"))):
    try:
        result = deliver_job(db, job_id=job_id, facility_id=facility_id, actor_user_id=user.id)
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=404 if "NOT_FOUND" in code else 409, detail=code) from exc

@router.get("/deliveries")
def deliveries(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission("reports.read"))):
    _ = user
    return [{"id": str(j.id), "patient_id": str(j.patient_id), "destination_node_id": str(j.destination_node_id), "status": j.status, "attempts": j.attempts, "max_attempts": j.max_attempts, "last_http_status": j.last_http_status, "last_error": j.last_error, "next_attempt_at": j.next_attempt_at.isoformat() if j.next_attempt_at else None, "delivered_at": j.delivered_at.isoformat() if j.delivered_at else None, "created_at": j.created_at.isoformat() if j.created_at else None} for j in list_jobs(db, facility_id, limit=limit)]

@router.get("/exports")
def exports(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    rows = list_export_logs(db, facility_id, limit=limit)
    return [
        {
            "id": str(r.id),
            "patient_id": str(r.patient_id),
            "export_type": r.export_type,
            "resource_count": r.resource_count,
            "purpose": r.purpose,
            "purpose_of_use": r.purpose_of_use,
            "destination": r.destination,
            "redacted_sensitive": r.redacted_sensitive,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/inbound/{inbound_id}/import")
def import_inbound(
    inbound_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.write")),
):
    try:
        result = import_inbound_clinical_resources(
            db,
            inbound_id=inbound_id,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        status_code = 404 if "NOT_FOUND" in code else 409 if code in {
            "INBOUND_DOCUMENT_NOT_ACCEPTED",
            "INBOUND_PATIENT_NOT_MATCHED",
            "INBOUND_SOURCE_NOT_TRUSTED",
        } else 400
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.get("/patients/{patient_id}/imported-resources")
def imported_patient_resources(
    patient_id: UUID,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = user
    rows = list_imported_patient_resources(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        limit=limit,
    )
    return [
        {
            "id": str(row.id),
            "resource_type": row.resource_type,
            "remote_resource_id": row.remote_resource_id,
            "purpose_of_use": row.purpose_of_use,
            "sensitivity": row.sensitivity,
            "normalized_code": row.normalized_code,
            "normalized_text": row.normalized_text,
            "effective_at": row.effective_at.isoformat() if row.effective_at else None,
            "source_provenance": row.source_provenance or {},
            "imported_at": row.imported_at.isoformat() if row.imported_at else None,
        }
        for row in rows
    ]
