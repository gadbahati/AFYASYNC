"""Build AfyaLink-shaped claim Bundle from local claim + invoice data."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.models import Invoice, InvoiceItem
from app.claims.models import Claim, ClaimItem
from app.coverage.models import Coverage
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import AfyaIdentity, Person
from app.sha_dha import config


def build_claim_bundle(
    db: Session,
    *,
    claim_id: UUID,
    facility_id: UUID,
) -> dict:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ValueError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")

    person = db.get(Person, claim.patient_id)
    if person is None:
        raise ValueError("PATIENT_NOT_FOUND")
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
    facility = db.get(Facility, facility_id)
    coverage = db.get(Coverage, invoice.coverage_id) if invoice.coverage_id else None
    encounter = db.get(Encounter, claim.encounter_id)

    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    claim_items = []
    for it in items:
        claim_items.append(
            {
                "productOrService": it.service_code,
                "quantity": float(it.quantity),
                "unitPrice": float(it.amount) / float(it.quantity) if it.quantity else float(it.amount),
                "currency": "KES",
                "category": "Procedure",
            }
        )
    if not claim_items:
        # Fallback single line from claim total
        claim_items.append(
            {
                "productOrService": "SHA-SERVICE",
                "quantity": 1,
                "unitPrice": float(claim.claim_amount or 0),
                "currency": "KES",
                "category": "Procedure",
            }
        )

    fid = getattr(facility, "code", None) or getattr(facility, "kmhfr_code", None) or str(facility_id)
    patient_ref = str(person.id)
    afya = identity.afya_id if identity else None
    coverage_id = (
        getattr(coverage, "membership_number", None)
        or getattr(coverage, "external_member_id", None)
        or (f"cov-{coverage.id}" if coverage else "cov-unknown")
    )

    period_start = None
    period_end = None
    if encounter and encounter.created_at:
        period_start = encounter.created_at.isoformat()
    if claim.submitted_at:
        period_end = claim.submitted_at.isoformat()
    elif claim.updated_at:
        period_end = claim.updated_at.isoformat()

    bundle_id = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": config.agent_code(),
        "entry": [
            {
                "resourceType": "Organization",
                "id": str(fid),
                "name": facility.name if facility else "Facility",
                "active": True,
                "identifier": str(fid),
            },
            {
                "resourceType": "Coverage",
                "identifier": str(coverage_id),
                "status": "active",
                "schemeCategory": "SOCIAL HEALTH AUTHORITY",
                "beneficiary": f"Patient/{patient_ref}",
            },
            {
                "resourceType": "Patient",
                "id": patient_ref,
                "name": f"{person.first_name} {person.last_name}".strip(),
                "gender": (person.sex or "unknown").lower(),
                "birthDate": person.date_of_birth.isoformat() if person.date_of_birth else None,
                "identifier": [{"system": "https://afyasync.health.ke/afya-id", "value": afya}] if afya else [],
            },
            {
                "resourceType": "Claim",
                "id": str(claim.id),
                "status": "active",
                "type": "institutional",
                "subType": "op",
                "patient": patient_ref,
                "billablePeriod": {"start": period_start, "end": period_end},
                "insurance": str(coverage_id),
                "provider": str(fid),
                "item": claim_items if len(claim_items) > 1 else claim_items[0],
                "total": {"value": float(claim.claim_amount or 0), "currency": "KES"},
                "localClaimNumber": claim.claim_id,
            },
        ],
        "meta": {
            "tag": [
                {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"},
                {"system": "https://afyasync.health.ke/source", "code": "AFYASYNC"},
            ]
        },
    }
    return bundle
