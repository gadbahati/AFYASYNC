from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.rbac.models import User
from app.interoperability.patient_schemas import FHIRPatientResource, FHIRPatientName

router = APIRouter(prefix="/api/v1/interoperability", tags=["Interoperability"])
PERMISSION = "interoperability.clinical.read"
FHIR_R4 = "4.0.1"

@router.get("/Patient/{patient_id}", response_model=FHIRPatientResource)
def read_patient(
    patient_id: UUID,
    access_reason: str = Query(min_length=3, max_length=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PERMISSION)),
) -> FHIRPatientResource:
    reason = " ".join(access_reason.split())
    row = db.execute(
        select(Person, AfyaIdentity)
        .join(PatientFacility, PatientFacility.patient_id == Person.id)
        .join(AfyaIdentity, AfyaIdentity.person_id == Person.id)
        .where(Person.id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="PATIENT_NOT_IN_FACILITY")
    patient, identity = row
    given = [x for x in [patient.first_name, patient.middle_name] if x]
    telecom = []
    if patient.phone:
        telecom.append({"system": "phone", "value": patient.phone})
    if patient.email:
        telecom.append({"system": "email", "value": patient.email})
    resource = FHIRPatientResource(
        id=patient.id,
        meta={"tag": [{"system": "urn:afyasync:interop", "code": f"fhir-r{FHIR_R4}"}]},
        active=patient.status == "ACTIVE",
        name=[FHIRPatientName(family=patient.last_name, given=given)],
        gender=(patient.sex or "").lower() or None,
        birthDate=patient.date_of_birth,
        telecom=telecom,
        identifier=[{"system": "urn:afyasync:afya-id", "value": identity.afya_id}],
    )
    record_audit(
        db, action="INTEROPERABILITY_PATIENT_READ", resource_type="PERSON",
        resource_id=str(patient_id), result="SUCCESS", user_id=user.id,
        facility_id=facility_id, patient_id=patient_id,
        metadata={"format":"FHIR_R4","reason_length":len(reason)}, commit=True
    )
    return resource
