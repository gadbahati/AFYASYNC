"""FHIR imaging representation for completed AfyaSync imaging orders."""
from __future__ import annotations
from datetime import timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.clinical.order_models import ClinicalOrder
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.terminology_service import canonical_coding
from app.patients.models import Person

KPS_IMAGING_STUDY_PROFILE="https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-imaging-study"
KPS_DIAGNOSTIC_REPORT_PROFILE="https://fhir.dha.go.ke/kps/StructureDefinition/ke-kps-diagnostic-report"
KENYA_CORE_SERVICEREQUEST_PROFILE="https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"
KENYA_CORE_TASK_PROFILE="https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"
KENYA_CORE_PROVENANCE_PROFILE="https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
DICOM_MODALITY_SYSTEM="http://dicom.nema.org/resources/ontology/DCM"
class ImagingFhirError(ValueError): pass

def build_imaging_bundle(db: Session, *, order_id: UUID, facility_id: UUID, actor_user_id: UUID | None) -> dict:
    order=db.get(ClinicalOrder,order_id)
    if order is None: raise ImagingFhirError("ORDER_NOT_FOUND")
    if order.facility_id!=facility_id: raise ImagingFhirError("FACILITY_ACCESS_DENIED")
    if order.order_type!="IMAGING": raise ImagingFhirError("ORDER_NOT_IMAGING")
    if order.status!="COMPLETED": raise ImagingFhirError("IMAGING_ORDER_NOT_COMPLETED")
    if not order.code: raise ImagingFhirError("IMAGING_CODE_REQUIRED")
    if not order.modality: raise ImagingFhirError("IMAGING_MODALITY_REQUIRED")
    if not order.impression: raise ImagingFhirError("IMAGING_IMPRESSION_REQUIRED")
    encounter=db.get(Encounter,order.encounter_id)
    person=db.get(Person,order.patient_id)
    if not encounter or encounter.facility_id!=facility_id: raise ImagingFhirError("ENCOUNTER_NOT_FOUND")
    if not person: raise ImagingFhirError("PATIENT_NOT_FOUND")
    study_type=canonical_coding(db,"AFYASYNC:IMAGING_STUDY",order.code,display=order.description)
    modality=canonical_coding(db,"AFYASYNC:IMAGING_MODALITY",order.modality,display=order.modality)
    if not study_type: raise ImagingFhirError("IMAGING_STUDY_NOT_NATIONALLY_MAPPED")
    if not modality: raise ImagingFhirError("IMAGING_MODALITY_NOT_NATIONALLY_MAPPED")
    patient=_patient_resource(db,person)
    patient["meta"]={"profile":["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    facility=_facility_organization_resource(db,facility_id)
    providers=actor_provider_identity_resources(db,user_id=actor_user_id,facility_id=facility_id)
    role=next((r for r in providers if r.get("resourceType")=="PractitionerRole"),None)
    performer={"reference":f"PractitionerRole/{role['id']}"} if role else {"reference":f"Organization/{facility_id}"}
    started=(order.updated_at or order.ordered_at).astimezone(timezone.utc).isoformat()
    sr={"resourceType":"ServiceRequest","id":f"imaging-servicerequest-{order.id}","meta":{"profile":[KENYA_CORE_SERVICEREQUEST_PROFILE]},
        "status":"completed","intent":"order","priority":{"URGENT":"urgent","STAT":"stat"}.get(order.priority,"routine"),
        "subject":{"reference":f"Patient/{person.id}"},"encounter":{"reference":f"Encounter/{encounter.id}"},
        "code":{"coding":[study_type],"text":order.description},"authoredOn":order.ordered_at.astimezone(timezone.utc).isoformat(),
        "requester":performer,"performer":[{"reference":f"Organization/{facility_id}"}]}
    task={"resourceType":"Task","id":f"imaging-task-{order.id}","meta":{"profile":[KENYA_CORE_TASK_PROFILE]},
          "status":"completed","intent":"order","priority":{"URGENT":"urgent","STAT":"stat"}.get(order.priority,"routine"),
          "code":{"coding":[study_type],"text":"Imaging order fulfilment"},"description":order.description,
          "focus":{"reference":f"ServiceRequest/{sr['id']}"},"for":{"reference":f"Patient/{person.id}"},
          "encounter":{"reference":f"Encounter/{encounter.id}"},"authoredOn":order.ordered_at.astimezone(timezone.utc).isoformat(),
          "owner":{"reference":f"Organization/{facility_id}"},"executionPeriod":{"start":order.ordered_at.astimezone(timezone.utc).isoformat(),"end":started}}
    study={"resourceType":"ImagingStudy","id":f"imaging-study-{order.id}","meta":{"profile":[KPS_IMAGING_STUDY_PROFILE]},
           "status":"available","subject":{"reference":f"Patient/{person.id}"},"started":started,
           "basedOn":[{"reference":f"ServiceRequest/{sr['id']}"}],"encounter":{"reference":f"Encounter/{encounter.id}"},
           "referrer":{"reference":performer},"modality":[modality],"description":order.description}
    report={"resourceType":"DiagnosticReport","id":f"imaging-report-{order.id}","meta":{"profile":[KPS_DIAGNOSTIC_REPORT_PROFILE]},
            "status":"final","code":{"coding":[study_type],"text":order.description},"subject":{"reference":f"Patient/{person.id}"},
            "encounter":{"reference":f"Encounter/{encounter.id}"},"effectiveDateTime":started,"issued":started,
            "performer":[performer],"basedOn":[{"reference":f"ServiceRequest/{sr['id']}"}],
            "imagingStudy":[{"reference":f"ImagingStudy/{study['id']}"}],"conclusion":order.impression}
    provenance={"resourceType":"Provenance","id":f"imaging-provenance-{order.id}","meta":{"profile":[KENYA_CORE_PROVENANCE_PROFILE]},
                "target":[{"reference":f"ImagingStudy/{study['id']}"},{"reference":f"DiagnosticReport/{report['id']}"}],
                "recorded":started,"agent":[{"type":{"text":"imaging performer"},"who":performer}],
                "reason":[{"text":"Imaging interoperability"}]}
    resources=[patient,facility,*providers,sr,task,study,report,provenance]
    bundle={"resourceType":"Bundle","id":f"imaging-fhir-{order.id}","type":"collection",
            "entry":[{"fullUrl":f"urn:uuid:{r['resourceType']}/{r['id']}","resource":r} for r in resources]}
    try: assert_valid_bundle(bundle)
    except ValueError as exc: raise ImagingFhirError(str(exc)) from exc
    return bundle
