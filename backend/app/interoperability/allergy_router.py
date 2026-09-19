from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.models import Allergy
from app.patients.models import PatientFacility
from app.database import get_db
from app.interoperability.allergy_schemas import (
    FHIRAllergyIntoleranceResource,
    FHIRAllergyReaction,
    FHIRCodeableConcept,
    FHIRReference,
)
from app.rbac.models import User


router = APIRouter(prefix="/api/v1/interoperability", tags=["Interoperability"])
CLINICAL_PERMISSION = "interoperability.clinical.read"

FHIR_R4 = "4.0.1"
US_CORE_ALLERGY_PROFILE = "http://hl7.org/fhir/us/core/StructureDefinition/us-core-allergyintolerance"

_SEVERITY_TO_CRITICALITY = {
    "LIFE_THREATENING": "high",
    "SEVERE": "high",
    "MODERATE": "high",
    "MILD": "low",
    "UNKNOWN": "unable-to-assess",
}


def _resource(allergy: Allergy) -> FHIRAllergyIntoleranceResource:
    status = "active" if allergy.status == "ACTIVE" else "inactive"
    severity = allergy.severity.upper()
    criticality = _SEVERITY_TO_CRITICALITY.get(severity, "unable-to-assess")
    reaction_text = (allergy.reaction or "").strip()

    reactions = []
    if reaction_text:
        reactions.append(
            FHIRAllergyReaction(
                manifestation=[
                    FHIRCodeableConcept(
                        text=reaction_text,
                        coding=[],
                    )
                ],
                description=reaction_text,
            )
        )

    notes = []
    if allergy.notes:
        notes.append(FHIRCodeableConcept(text=allergy.notes))

    return FHIRAllergyIntoleranceResource(
        id=allergy.id,
        meta={
            "profile": [US_CORE_ALLERGY_PROFILE],
            "tag": [{"system": "urn:afyasync:interop", "code": f"fhir-r{FHIR_R4}"}],
        },
        clinicalStatus=FHIRCodeableConcept(
            coding=[{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                "code": status,
            }],
            text=status,
        ),
        verificationStatus=FHIRCodeableConcept(
            coding=[{
                "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                "code": "confirmed",
            }],
            text="confirmed",
        ),
        criticality=criticality,
        code=FHIRCodeableConcept(
            coding=[{
                "system": "urn:afyasync:allergen",
                "code": allergy.allergen.strip(),
                "display": allergy.allergen.strip(),
            }],
            text=allergy.allergen.strip(),
        ),
        patient=FHIRReference(reference=f"Patient/{allergy.patient_id}"),
        onsetDateTime=allergy.onset_date,
        recordedDate=allergy.created_at.date() if allergy.created_at else None,
        reaction=reactions,
        note=notes,
    )


@router.get("/AllergyIntolerance/{patient_id}", response_model=list[FHIRAllergyIntoleranceResource])
def read_allergies(
    patient_id: UUID,
    access_reason: str = Query(min_length=3, max_length=200),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLINICAL_PERMISSION)),
) -> list[FHIRAllergyIntoleranceResource]:
    reason = " ".join(access_reason.split())
    enrolled = db.scalar(
        select(PatientFacility.patient_id)
        .where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
        .limit(1)
    )
    if enrolled is None:
        raise HTTPException(status_code=404, detail="PATIENT_NOT_IN_FACILITY")

    stmt = select(Allergy).where(
        Allergy.patient_id == patient_id,
        Allergy.facility_id == facility_id,
    )
    if not include_inactive:
        stmt = stmt.where(Allergy.status == "ACTIVE")

    allergies = list(db.scalars(stmt.order_by(Allergy.updated_at.desc(), Allergy.created_at.desc())).all())
    record_audit(
        db,
        action="INTEROPERABILITY_ALLERGY_READ",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={
            "format": "FHIR_R4",
            "profile": US_CORE_ALLERGY_PROFILE,
            "count": len(allergies),
            "include_inactive": include_inactive,
            "reason_length": len(reason),
        },
        commit=True,
    )
    return [_resource(item) for item in allergies]
