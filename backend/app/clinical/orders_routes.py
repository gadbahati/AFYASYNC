"""Clinical orders routes — Phase 153: pharmacy dispense_qty / batch_no.

Developed by BAHATI GAD WANGWE.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.department_bridge import forward_clinical_order
from app.clinical.fulfillment_service import fulfill_order
from app.clinical.order_service import (
    OrderError,
    create_order,
    list_orders,
    order_to_dict,
    update_order_status,
)
from app.database import get_db
from app.rbac.models import User

orders_router = APIRouter(tags=["Clinical Orders"])


def _http(exc: Exception) -> HTTPException:
    code = str(exc)
    status_code = (
        404
        if "NOT_FOUND" in code
        else (
            403
            if "DENIED" in code
            else 409
            if "CANCELLED" in code or "ALREADY_COMPLETED" in code or "COMPLETED" in code
            else 400
        )
    )
    return HTTPException(status_code=status_code, detail=code)


@orders_router.get("/{encounter_id}/orders")
def get_orders(
    encounter_id: UUID,
    order_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.record.read")),
):
    _ = user
    try:
        rows = list_orders(
            db, encounter_id=encounter_id, facility_id=facility_id, order_type=order_type
        )
    except OrderError as exc:
        raise _http(exc) from exc
    return [order_to_dict(r) for r in rows]


@orders_router.post("/{encounter_id}/orders", status_code=201)
def post_order(
    encounter_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.note.write")),
):
    try:
        row = create_order(
            db,
            encounter_id=encounter_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            order_type=str(payload.get("order_type") or ""),
            description=str(payload.get("description") or ""),
            code=payload.get("code"),
            priority=str(payload.get("priority") or "ROUTINE"),
            notes=payload.get("notes"),
        )
    except OrderError as exc:
        raise _http(exc) from exc
    return order_to_dict(row)


@orders_router.patch("/orders/{order_id}/status")
def patch_order_status(
    order_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.note.write")),
):
    try:
        row = update_order_status(
            db,
            order_id=order_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            status=str(payload.get("status") or ""),
        )
    except OrderError as exc:
        raise _http(exc) from exc
    return order_to_dict(row)


@orders_router.post("/orders/{order_id}/fulfill")
def post_fulfill_order(
    order_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.note.write")),
):
    try:
        row = fulfill_order(
            db,
            order_id=order_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            status=str(payload.get("status") or "COMPLETED"),
            result_notes=payload.get("result_notes"),
            modality=payload.get("modality"),
            impression=payload.get("impression"),
            lab_value=payload.get("lab_value"),
            lab_units=payload.get("lab_units"),
            lab_flag=payload.get("lab_flag"),
            dispense_qty=payload.get("dispense_qty"),
            batch_no=payload.get("batch_no"),
        )
    except OrderError as exc:
        raise _http(exc) from exc
    return order_to_dict(row)


@orders_router.post("/orders/{order_id}/forward")
def post_forward_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.note.write")),
):
    try:
        result = forward_clinical_order(
            db,
            order_id=order_id,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
    except OrderError as exc:
        raise _http(exc) from exc
    except Exception as exc:
        raise _http(exc) from exc
    return result
