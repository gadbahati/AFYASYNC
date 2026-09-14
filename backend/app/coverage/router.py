from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.coverage.adjudication_schemas import BenefitAdjudicationRequest, BenefitAdjudicationResponse
from app.coverage.adjudication_service import adjudicate_benefit
from app.coverage.models import Payer, PayerPlan
from app.coverage.permissions import COVERAGE_BENEFIT_WRITE, COVERAGE_READ, COVERAGE_WRITE
from app.coverage.schemas import BenefitRuleCreate, BenefitRuleResponse, CoverageCreate, CoverageResponse, PayerPlanResponse, PayerResponse
from app.coverage.service import create_benefit_rule, create_coverage, get_active_coverage, verify_coverage
from app.database import get_db
from app.patients.models import PatientFacility
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/coverage", tags=["Coverage"])


def _require_patient_enrolled(db: Session, person_id: UUID, facility_id: UUID) -> None:
    membership = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == person_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PATIENT_NOT_IN_FACILITY")


@router.get("/payers", response_model=list[PayerResponse])
def list_payers(db: Session = Depends(get_db), _: User = Depends(require_permission(COVERAGE_READ)), __: UUID = Depends(get_facility_context)) -> list[PayerResponse]:
    return list(db.scalars(select(Payer).where(Payer.status == "ACTIVE").order_by(Payer.code)))


@router.get("/payers/{payer_id}/plans", response_model=list[PayerPlanResponse])
def list_payer_plans(payer_id: UUID, db: Session = Depends(get_db), _: User = Depends(require_permission(COVERAGE_READ)), __: UUID = Depends(get_facility_context)) -> list[PayerPlanResponse]:
    payer = db.get(Payer, payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PAYER_NOT_FOUND")
    return list(db.scalars(select(PayerPlan).where(PayerPlan.payer_id == payer_id, PayerPlan.status == "ACTIVE").order_by(PayerPlan.code)))


@router.post("", response_model=CoverageResponse, status_code=status.HTTP_201_CREATED)
def add_coverage(payload: CoverageCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(COVERAGE_WRITE))) -> CoverageResponse:
    _require_patient_enrolled(db, payload.person_id, facility_id)
    try:
        return create_coverage(db, payload, actor_user_id=user.id)
    except ValueError as err:
        code = str(err)
        messages = {"INVALID_COVERAGE_DATES": "Coverage end date cannot be before start date.", "PAYER_NOT_FOUND": "The selected payer is not available.", "INVALID_PAYER_PLAN": "The selected payer plan is invalid."}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages.get(code, code)}) from err


@router.post("/{coverage_id}/verify", response_model=CoverageResponse)
def confirm_coverage(coverage_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(COVERAGE_WRITE))) -> CoverageResponse:
    try:
        coverage = verify_coverage(db, coverage_id, actor_user_id=user.id)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err
    _require_patient_enrolled(db, coverage.person_id, facility_id)
    return coverage


@router.get("/person/{person_id}/active", response_model=list[CoverageResponse])
def active_coverage_self(person_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[CoverageResponse]:
    if user.person_id != person_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="COVERAGE_ACCESS_DENIED")
    return get_active_coverage(db, person_id)


@router.get("/facility/person/{person_id}/active", response_model=list[CoverageResponse])
def active_coverage_for_facility(person_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(COVERAGE_READ))) -> list[CoverageResponse]:
    _require_patient_enrolled(db, person_id, facility_id)
    return get_active_coverage(db, person_id)


@router.post("/adjudicate", response_model=BenefitAdjudicationResponse)
def adjudicate(payload: BenefitAdjudicationRequest, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(COVERAGE_READ))) -> BenefitAdjudicationResponse:
    try:
        return adjudicate_benefit(db, payload=payload, facility_id=facility_id, actor_user_id=user.id)
    except ValueError as err:
        code = str(err)
        mapping = {
            "COVERAGE_NOT_ACTIVE": (404, "Coverage is not active."),
            "COVERAGE_NOT_VERIFIED": (409, "Coverage must be verified before benefit adjudication."),
            "COVERAGE_NOT_YET_ACTIVE": (409, "Coverage is not yet effective."),
            "COVERAGE_EXPIRED": (409, "Coverage has expired."),
            "PATIENT_NOT_IN_FACILITY": (404, "Patient is not enrolled at this facility."),
            "COVERAGE_PLAN_NOT_ACTIVE": (409, "The coverage plan is not active."),
            "BENEFIT_SCOPE_REQUIRED": (400, "Provide a service code or service type."),
        }
        http_status, message = mapping.get(code, (400, code))
        raise HTTPException(status_code=http_status, detail={"code": code, "message": message}) from err


@router.post("/benefit-rules", response_model=BenefitRuleResponse, status_code=status.HTTP_201_CREATED)
def add_benefit_rule(payload: BenefitRuleCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(COVERAGE_BENEFIT_WRITE))) -> BenefitRuleResponse:
    _ = facility_id
    try:
        return create_benefit_rule(db, payload, actor_user_id=user.id)
    except ValueError as err:
        code = str(err)
        messages = {"INVALID_BENEFIT_DATES": "Benefit rule end date cannot be before its start date.", "PAYER_NOT_FOUND": "The selected payer is not available.", "INVALID_PAYER_PLAN": "The selected payer plan is invalid."}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages.get(code, code)}) from err
