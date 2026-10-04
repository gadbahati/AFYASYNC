"""Phase 132 order routes — mounted on clinical encounter router."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.order_service import OrderError, create_order, list_orders, order_to_dict, update_order_status
from app.database import get_db
from app.rbac.models import User

orders_router = APIRouter()


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
        rows = list_orders(db, encounter_id=encounter_id, facility_id=facility_id, order_type=order_type)
    except OrderError as exc:
        code = str(exc)
        status_code = 404 if code == "ENCOUNTER_NOT_FOUND" else 403
        raise HTTPException(status_code=status_code, detail=code) from exc
    return [order_to_dict(x) for x in rows]


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
        code = str(exc)
        status_code = 404 if code == "ENCOUNTER_NOT_FOUND" else (403 if code == "FACILITY_ACCESS_DENIED" else 409)
        raise HTTPException(status_code=status_code, detail=code) from exc
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
        code = str(exc)
        status_code = 404 if code == "ORDER_NOT_FOUND" else (403 if code == "FACILITY_ACCESS_DENIED" else 409)
        raise HTTPException(status_code=status_code, detail=code) from exc
    return order_to_dict(row)
