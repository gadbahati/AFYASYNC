from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.benefits.models import BenefitPackage


def list_active_benefit_packages(
    db: Session,
    *,
    facility_id: UUID,
    actor_user_id: UUID,
) -> list[BenefitPackage]:
    packages = list(
        db.scalars(
            select(BenefitPackage)
            .where(BenefitPackage.status == "ACTIVE")
            .order_by(BenefitPackage.package_code)
        ).all()
    )
    record_audit(
        db,
        action="VIEW_BENEFIT_PACKAGES",
        resource_type="BENEFIT_PACKAGE",
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"package_count": len(packages)},
        commit=False,
    )
    db.commit()
    return packages
