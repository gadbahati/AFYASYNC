from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Coverage, Payer
from app.coverage.service import calculate_charge_responsibility
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.preauthorization.models import Preauthorization
from app.preauthorization.schemas import PreauthorizationCreate, PreauthorizationResponse


def create_preauthorization(
    db: Session,
    payload: PreauthorizationCreate,
    *,
    facility_id: UUID,
    actor_user_id: UUID,
) -> PreauthorizationResponse:
    patient_link = db.scalar(
        select(PatientFacility).where(
            PatientFacility.patient_id == payload.patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if patient_link is None:
        raise ValueError("PATIENT_FACILITY_ACCESS_DENIED")

    person = db.get(Person, payload.patient_id)
    if person is None or person.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")

    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
    if identity is None or identity.status != "ACTIVE":
        raise ValueError("IDENTITY_NOT_ACTIVE")

    coverage = db.scalar(
        select(Coverage).where(
            Coverage.id == payload.coverage_id,
            Coverage.person_id == payload.patient_id,
            Coverage.status == "ACTIVE",
            Coverage.verification_status == "VERIFIED",
            (Coverage.start_date.is_(None) | (Coverage.start_date <= date.today())),
            (Coverage.end_date.is_(None) | (Coverage.end_date >= date.today())),
        )
    )
    if coverage is None:
        raise ValueError("VERIFIED_CURRENT_COVERAGE_REQUIRED")

    payer = db.get(Payer, coverage.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_ACTIVE")

    try:
        payer_amount, patient_amount, _ = calculate_charge_responsibility(
            db,
            coverage,
            amount=payload.requested_amount,
            service_code=payload.service_code,
            service_type=payload.service_type,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    duplicate = db.scalar(
        select(Preauthorization.id).where(
            Preauthorization.patient_id == payload.patient_id,
            Preauthorization.facility_id == facility_id,
            Preauthorization.coverage_id == coverage.id,
            Preauthorization.service_code == payload.service_code,
            Preauthorization.status.in_(["PENDING", "APPROVED"]),
        ).limit(1)
    )
    if duplicate is not None:
        raise ValueError("DUPLICATE_ACTIVE_PREAUTHORIZATION")

    request = Preauthorization(
        id=uuid4(),
        patient_id=payload.patient_id,
        facility_id=facility_id,
        coverage_id=coverage.id,
        payer_id=coverage.payer_id,
        service_code=payload.service_code,
        service_type=payload.service_type,
        requested_amount=payload.requested_amount.quantize(Decimal("0.01")),
        status="PENDING",
        reason=payload.reason,
        created_by=actor_user_id,
    )
    db.add(request)
    db.flush()
    record_audit(
        db,
        action="CREATE_PREAUTHORIZATION",
        resource_type="PREAUTHORIZATION",
        resource_id=str(request.id),
        result="PENDING",
        user_id=actor_user_id,
        patient_id=payload.patient_id,
        metadata={
            "facility_id": str(facility_id),
            "coverage_id": str(coverage.id),
            "payer_id": str(coverage.payer_id),
            "service_code": payload.service_code,
            "requested_amount": str(request.requested_amount),
            "payer_estimate": str(payer_amount),
            "patient_estimate": str(patient_amount),
        },
        commit=False,
    )
    db.commit()
    db.refresh(request)
    return PreauthorizationResponse.model_validate(request)
