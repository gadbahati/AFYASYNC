from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_government_context
from app.database import get_db
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import PatientFacility
from app.claims.models import Claim
from app.tenancy.models import OrganizationFacility

router = APIRouter(prefix="/api/v1/government", tags=["government"])


@router.get("/overview")
def government_overview(context=Depends(get_government_context), db: Session = Depends(get_db)):
    organization = context["organization"]
    access = context["access"]
    facility_ids = list(db.scalars(
        select(OrganizationFacility.facility_id)
        .join(Facility, Facility.id == OrganizationFacility.facility_id)
        .where(
            OrganizationFacility.organization_id == organization.id,
            OrganizationFacility.status == "ACTIVE",
            Facility.status == "ACTIVE",
        )
    ).all())
    facilities = list(db.scalars(
        select(Facility).where(Facility.id.in_(facility_ids)).order_by(Facility.county, Facility.name).limit(500)
    ).all()) if facility_ids else []

    def count(model):
        if not facility_ids:
            return 0
        return int(db.scalar(select(func.count()).select_from(model).where(model.facility_id.in_(facility_ids))) or 0)

    patients = 0
    if facility_ids:
        patients = int(db.scalar(
            select(func.count(func.distinct(PatientFacility.patient_id))).where(
                PatientFacility.facility_id.in_(facility_ids),
                PatientFacility.status == "ACTIVE",
            )
        ) or 0)

    return {
        "success": True,
        "data": {
            "portal_type": "government",
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "code": organization.code,
                "type": organization.organization_type,
            },
            "authorization": {
                "role_code": access.role_code,
                "scope_level": access.scope_level,
                "facility_count": len(facility_ids),
                "patient_identifiers_exposed": False,
            },
            "aggregates": {
                "facilities": len(facility_ids),
                "patients": patients,
                "encounters": count(Encounter),
                "claims": count(Claim),
            },
            "facilities": [
                {"id": str(f.id), "name": f.name, "county": f.county, "status": f.status}
                for f in facilities
            ],
            "data_policy": "Government portal defaults to governed aggregates. Identifiable patient records require separate endpoint-level authorization and lawful purpose.",
        },
    }
