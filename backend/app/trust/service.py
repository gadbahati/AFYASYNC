"""Public trust content — hardened: zero PHI, zero internal secrets."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.facilities.models import Facility
from app.trust.schemas import (
    Attribution,
    PublicFacilityCard,
    PublicStatus,
    PublicTrustBundle,
    TrustPrinciples,
)

DEVELOPER = "BAHATI GAD WANGWE"


def public_status() -> PublicStatus:
    env = (settings.environment or "development").lower()
    # Do not leak whether this is a specific prod host
    label = "production" if env == "production" else "non-production"
    return PublicStatus(
        service="afyasync-api",
        status="operational",
        version=settings.app_version,
        environment_label=label,
        standalone_first=True,
        sha_integrated_not_clone=True,
    )


def attribution() -> Attribution:
    return Attribution(
        product="AfyaSync",
        developed_by=DEVELOPER,
        year=2026,
        notice=(
            "AfyaSync is the exclusive intellectual property of BAHATI GAD WANGWE. "
            "Unauthorized copying, redistribution, reverse engineering, or rebranding "
            "without written permission is prohibited."
        ),
        prohibited=[
            "Copy or redistribute source code without authorization",
            "Reverse engineer or rebrand as another product",
            "Remove copyright or developer attribution",
            "Exfiltrate patient data outside lawful facility/patient consent paths",
        ],
    )


def trust_principles() -> TrustPrinciples:
    return TrustPrinciples(
        title="AfyaSync Public Trust Principles",
        principles=[
            "Standalone first: cash and local operations work without SHA online",
            "Patient-controlled sensitive disclosure with on-screen consent",
            "Multi-payer truth and out-of-pocket estimates before care",
            "Prescribe-time allergy and medication safety checks",
            "Appointment capacity and FIFO fairness",
            "Audit trails on clinical and coverage actions",
            "No public endpoint exposes identifiable patient data",
        ],
        data_protection=[
            "Aligned with Kenya Data Protection Act principles (lawfulness, purpose limitation, minimisation)",
            "Sensitive diagnoses require explicit patient consent for cross-facility share",
            "Public APIs never return names, IDs, diagnoses, or claims of individuals",
            "Facility staff access is permission-scoped and audited",
        ],
        patient_rights=[
            "Create and use an Afya ID / portal account",
            "Request appointments and receive facility responses",
            "View continuity card snapshots subject to consent rules",
            "Estimate out-of-pocket across active coverages",
            "Refuse sensitive disease disclosure into the shared record",
        ],
        government_alignment=[
            "SHA is integrated as a payer path — not the only operating mode",
            "Claim preflight and rejection prevention improve quality of submissions",
            "County care-gap intelligence uses aggregates, not individual dossiers",
            "Interoperability exports support standards-oriented exchange",
        ],
        developer=DEVELOPER,
        copyright_notice=f"© 2026 AfyaSync. Developed by {DEVELOPER}. All rights reserved.",
    )


def list_public_facilities(db: Session, *, county: str | None = None, limit: int = 100) -> list[PublicFacilityCard]:
    limit = max(1, min(limit, 200))
    stmt = select(Facility).where(Facility.status == "ACTIVE")
    if county:
        stmt = stmt.where(Facility.county.ilike(county.strip()))
    rows = list(db.scalars(stmt.order_by(Facility.name.asc()).limit(limit)))
    return [
        PublicFacilityCard(
            facility_code=f.facility_id,
            name=f.name,
            facility_type=f.facility_type,
            county=f.county,
            sub_county=f.sub_county,
            phone=f.phone,
        )
        for f in rows
    ]


def count_active_facilities(db: Session) -> int:
    return int(
        db.scalar(select(func.count()).select_from(Facility).where(Facility.status == "ACTIVE"))
        or 0
    )


def trust_bundle(db: Session) -> PublicTrustBundle:
    return PublicTrustBundle(
        status=public_status(),
        attribution=attribution(),
        principles_summary=(
            "AfyaSync is a facility operating system with multi-payer support and a patient portal. "
            "Built for hospitals, individuals, and government — not a SHA clone."
        ),
        facility_count_active=count_active_facilities(db),
        endpoints=[
            "GET /api/v1/public/trust",
            "GET /api/v1/public/principles",
            "GET /api/v1/public/status",
            "GET /api/v1/public/attribution",
            "GET /api/v1/public/facilities",
            "GET /api/v1/public/privacy",
        ],
    )
