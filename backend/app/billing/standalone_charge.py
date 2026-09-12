from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Service
from app.billing.service import BillingError
from app.encounters.models import Encounter


class StandaloneChargeCreate(BaseModel):
    encounter_id: UUID
    service_id: UUID
    quantity: float = Field(gt=0)
    unit_price: float | None = Field(default=None, gt=0)
    source_type: str = Field(min_length=1, max_length=50)
    source_id: UUID | None = None


def create_standalone_charge(db: Session, facility_id: UUID, payload: dict, *, actor_user_id: UUID | None = None) -> Charge:
    encounter = db.get(Encounter, payload["encounter_id"])
    if encounter is None:
        raise BillingError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    service = db.get(Service, payload["service_id"])
    if service is None or service.status != "ACTIVE":
        raise BillingError("SERVICE_NOT_FOUND")
    if service.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    quantity = Decimal(str(payload["quantity"]))
    unit_price = Decimal(str(payload.get("unit_price") if payload.get("unit_price") is not None else service.price))
    if quantity <= 0 or unit_price <= 0:
        raise BillingError("INVALID_CHARGE_AMOUNT")
    total = (quantity * unit_price).quantize(Decimal("0.01"))
    charge = Charge(charge_id=f"CHG-{uuid4().hex[:20].upper()}", encounter_id=encounter.id, patient_id=encounter.patient_id, facility_id=facility_id, service_id=service.id, quantity=quantity, unit_price=unit_price, total_amount=total, source_type=payload["source_type"], source_id=payload.get("source_id"))
    db.add(charge)
    db.flush()
    record_audit(db, action="CREATE_CHARGE", resource_type="CHARGE", resource_id=str(charge.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=encounter.patient_id, metadata={"charge_id": charge.charge_id, "amount": str(total), "unit_price": str(unit_price), "standalone_price": payload.get("unit_price") is not None}, commit=False)
    db.commit()
    db.refresh(charge)
    return charge
