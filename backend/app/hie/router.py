"""HIE depth APIs — robust national exchange."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.hie.service import (
    build_patient_summary_bundle,
    build_referral_package,
    capability_statement,
    list_export_logs,
    list_nodes,
    upsert_node,
    validate_inbound_bundle,
)
from app.rbac.models import User

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


@router.get("/metadata")
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
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
