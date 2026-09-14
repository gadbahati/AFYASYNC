from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Coverage, Payer, PayerPlan
from app.coverage.sha_eligibility_schemas import SHAEligibilityResponse
from app.integrations.adapters import AdapterResult, build_adapter
from app.integrations.models import Integration
from app.patients.models import AfyaIdentity, PatientFacility, Person


class SHAEligibilityError(ValueError):
    pass


def _parse_date(value, field: str) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise SHAEligibilityError(f"INVALID_SHA_RESPONSE_{field.upper()}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SHAEligibilityError(f"INVALID_SHA_RESPONSE_{field.upper()}") from exc


def _normalise_response(result: AdapterResult) -> dict:
    if result.status == "RETRYING":
        raise SHAEligibilityError("SHA_ELIGIBILITY_UNAVAILABLE")
    if result.status != "SUCCEEDED" or not isinstance(result.response_data, dict):
        raise SHAEligibilityError("SHA_ELIGIBILITY_FAILED")
    data = result.response_data
    if not isinstance(data.get("eligible"), bool):
        raise SHAEligibilityError("INVALID_SHA_RESPONSE")
    membership = data.get("membership_number")
    if membership is not None and (not isinstance(membership, str) or not membership.strip()):
        raise SHAEligibilityError("INVALID_SHA_RESPONSE_MEMBERSHIP")
    if membership is not None:
        data = {**data, "membership_number": membership.strip().upper()}
    external_reference = result.external_reference
    if external_reference is not None and (not isinstance(external_reference, str) or len(external_reference) > 150):
        raise SHAEligibilityError("INVALID_SHA_RESPONSE_EXTERNAL_REFERENCE")
    return data


def verify_sha_eligibility(
    db: Session,
    *,
    facility_id: UUID,
    person_id: UUID,
    membership_number: str,
    actor_user_id: UUID,
) -> SHAEligibilityResponse:
    membership = membership_number.strip().upper()
    if not membership:
        raise SHAEligibilityError("MEMBERSHIP_NUMBER_REQUIRED")

    enrolled = db.scalar(select(PatientFacility.id).where(
        PatientFacility.patient_id == person_id,
        PatientFacility.facility_id == facility_id,
        PatientFacility.status == "ACTIVE",
    ))
    if enrolled is None:
        raise SHAEligibilityError("PATIENT_NOT_IN_FACILITY")

    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id, AfyaIdentity.status == "ACTIVE"))
    if identity is None:
        raise SHAEligibilityError("AFYA_ID_NOT_ACTIVE")

    payer = db.scalar(select(Payer).where(Payer.code == "SHA", Payer.status == "ACTIVE"))
    if payer is None:
        raise SHAEligibilityError("SHA_PAYER_NOT_CONFIGURED")

    integration = db.scalar(select(Integration).where(
        Integration.facility_id == facility_id,
        Integration.provider == "SHA",
        Integration.integration_type == "PAYER",
        Integration.status == "ACTIVE",
    ).order_by(Integration.created_at.desc()).limit(1))
    if integration is None:
        raise SHAEligibilityError("SHA_INTEGRATION_NOT_CONFIGURED")

    configuration = integration.configuration or {}
    if configuration.get("adapter_type") != "http_json":
        raise SHAEligibilityError("SHA_CONNECTOR_NOT_CONFIGURED")

    db.rollback()
    try:
        adapter = build_adapter(configuration)
        result = adapter.send(
            {
                "operation": "ELIGIBILITY_CHECK",
                "payer": "SHA",
                "afya_id": identity.afya_id,
                "membership_number": membership,
            },
            f"SHA-ELIGIBILITY-{person_id}-{membership}",
        )
    except ValueError as exc:
        raise SHAEligibilityError(str(exc)) from exc
    except Exception as exc:
        raise SHAEligibilityError("SHA_ELIGIBILITY_UNAVAILABLE") from exc

    data = _normalise_response(result)
    response_membership = data.get("membership_number") or membership
    if response_membership.strip().upper() != membership:
        raise SHAEligibilityError("SHA_MEMBERSHIP_MISMATCH")

    start_date = _parse_date(data.get("start_date"), "start_date")
    end_date = _parse_date(data.get("end_date"), "end_date")
    if start_date and end_date and end_date < start_date:
        raise SHAEligibilityError("INVALID_SHA_RESPONSE_DATES")

    plan_id = None
    plan_code = data.get("plan_code")
    if plan_code is not None:
        if not isinstance(plan_code, str) or not plan_code.strip() or len(plan_code.strip()) > 50:
            raise SHAEligibilityError("INVALID_SHA_RESPONSE_PLAN")
        plan = db.scalar(select(PayerPlan).where(
            PayerPlan.payer_id == payer.id,
            PayerPlan.code == plan_code.strip(),
            PayerPlan.status == "ACTIVE",
        ))
        if plan is None:
            raise SHAEligibilityError("SHA_PLAN_NOT_CONFIGURED")
        plan_id = plan.id

    coverage = db.scalar(select(Coverage).where(
        Coverage.person_id == person_id,
        Coverage.payer_id == payer.id,
        Coverage.membership_number == membership,
        Coverage.status == "ACTIVE",
    ).order_by(Coverage.created_at.desc()).limit(1))

    if coverage is None:
        coverage = Coverage(
            person_id=person_id,
            payer_id=payer.id,
            payer_plan_id=plan_id,
            membership_number=membership,
            start_date=start_date,
            end_date=end_date,
            verification_status="VERIFIED" if data["eligible"] else "UNVERIFIED",
            status="ACTIVE",
        )
        db.add(coverage)
    else:
        if plan_id is not None:
            coverage.payer_plan_id = plan_id
        coverage.start_date = start_date
        coverage.end_date = end_date
        coverage.verification_status = "VERIFIED" if data["eligible"] else "UNVERIFIED"

    db.flush()
    record_audit(
        db,
        action="SHA_ELIGIBILITY_CHECK",
        resource_type="COVERAGE",
        resource_id=str(coverage.id),
        result="ELIGIBLE" if data["eligible"] else "INELIGIBLE",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person_id,
        metadata={
            "payer_id": str(payer.id),
            "integration_id": str(integration.id),
            "membership_number": membership,
            "eligible": data["eligible"],
            "external_reference": result.external_reference,
        },
        commit=False,
    )
    db.commit()
    db.refresh(coverage)

    return SHAEligibilityResponse(
        coverage_id=coverage.id,
        person_id=person_id,
        payer_id=payer.id,
        payer_plan_id=coverage.payer_plan_id,
        membership_number=membership,
        eligible=data["eligible"],
        verification_status=coverage.verification_status,
        start_date=coverage.start_date,
        end_date=coverage.end_date,
        external_reference=result.external_reference,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )
