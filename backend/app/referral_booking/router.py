from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.referrals.models import Referral
from .schemas import BookingCreate, BookingOut
from .service import BookingError, book
router = APIRouter(prefix="/api/v1/referral-booking", tags=["Referral booking exchange"])

def _out(db: Session, row):
    referral = db.get(Referral, row.referral_id)
    if referral is None: raise HTTPException(status_code=500, detail="BOOKING_REFERRAL_MISSING")
    return BookingOut(booking_id=row.id, booking_reference=row.booking_reference, referral_id=row.referral_id, appointment_id=row.appointment_id, coordination_case_id=row.coordination_case_id, status=row.status, patient_id=row.patient_id, source_facility_id=row.source_facility_id, destination_facility_id=row.destination_facility_id, destination_department_id=referral.destination_department_id, service_code=row.service_code, network_code=row.network_code, appointment_at=row.appointment_at)

@router.post("/book", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create(payload: BookingCreate, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"), user: User = Depends(require_permission("referrals.create")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    if not idempotency_key: raise HTTPException(status_code=400, detail="IDEMPOTENCY_KEY_REQUIRED")
    try: return _out(db, book(db, source_facility_id=facility_id, actor_user_id=user.id, payload=payload.model_dump(), idempotency_key=idempotency_key))
    except BookingError as exc:
        mapping = {"PATIENT_NOT_FOUND":404,"INVALID_SOURCE_ENCOUNTER":409,"INVALID_DESTINATION_FACILITY":404,"INVALID_DESTINATION_DEPARTMENT":404,"NETWORK_REFERRAL_NOT_ENABLED":409,"SERVICE_NOT_AVAILABLE":404,"SERVICE_DEPARTMENT_MISMATCH":409,"APPOINTMENT_IN_PAST":400,"OUTSIDE_OPERATING_HOURS":409,"DEPARTMENT_DAY_FULL":409,"SLOT_UNAVAILABLE":409,"PATIENT_ALREADY_BOOKED_THAT_DAY":409,"FACILITY_ACCESS_DENIED":403,"STAFF_CONTEXT_REQUIRED":403,"INVALID_IDEMPOTENCY_KEY":400}
        raise HTTPException(status_code=mapping.get(str(exc),400), detail=str(exc)) from exc
