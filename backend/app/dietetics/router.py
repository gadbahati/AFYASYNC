from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_db, require_permission
from app.dietetics.schemas import (
    DietOrderCreate,
    DietOrderResponse,
    DietOrderStatusUpdate,
    NutritionAssessmentCreate,
    NutritionAssessmentResponse,
)
from app.dietetics.service import (
    assess_nutrition,
    list_patient_diet_orders,
    order_diet,
    update_diet_order_status,
)

router = APIRouter(prefix="/api/v1/dietetics", tags=["Dietetics"])


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    if code == "PATIENT_NOT_IN_FACILITY":
        return HTTPException(status.HTTP_403_FORBIDDEN, detail="Patient is not actively enrolled at this facility")
    if code == "DIET_ORDER_NOT_FOUND":
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="Diet order not found")
    if code == "ENCOUNTER_NOT_FOUND":
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="Encounter not found for this patient and facility")
    if code == "ENCOUNTER_NOT_OPEN":
        return HTTPException(status.HTTP_409_CONFLICT, detail="Encounter is not open for a new dietetics order")
    return HTTPException(status.HTTP_400_BAD_REQUEST, detail=code)


@router.post("/assessments", response_model=NutritionAssessmentResponse, status_code=status.HTTP_201_CREATED)
def assessment(
    payload: NutritionAssessmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("encounters.create")),
):
    try:
        return assess_nutrition(db, user.facility_id, user.id, payload)
    except ValueError as exc:
        raise _error(exc)


@router.post("/orders", response_model=DietOrderResponse, status_code=status.HTTP_201_CREATED)
def diet_order(
    payload: DietOrderCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("encounters.create")),
):
    try:
        return order_diet(db, user.facility_id, user.id, payload)
    except ValueError as exc:
        raise _error(exc)


@router.get("/patients/{patient_id}/orders", response_model=list[DietOrderResponse])
def patient_orders(
    patient_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("patients.record.read")),
):
    try:
        return list_patient_diet_orders(db, user.facility_id, patient_id)
    except ValueError as exc:
        raise _error(exc)


@router.patch("/orders/{order_id}/status", response_model=DietOrderResponse)
def order_status(
    order_id: UUID,
    payload: DietOrderStatusUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("encounters.create")),
):
    try:
        return update_diet_order_status(db, user.facility_id, user.id, order_id, payload.status)
    except ValueError as exc:
        raise _error(exc)
