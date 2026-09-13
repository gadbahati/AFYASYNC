from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.admissions.models import Admission
from app.wards.models import Bed, BedAssignment, Ward
from app.wards.movement import PatientMovement


def transfer_patient(db: Session, facility_id: UUID, actor: UUID, admission_id: UUID, to_bed_id: UUID, reason: str | None = None):
    admission = db.scalar(select(Admission).where(Admission.id == admission_id, Admission.facility_id == facility_id).with_for_update())
    new_bed = db.scalar(select(Bed).join(Ward).where(Bed.id == to_bed_id, Ward.facility_id == facility_id).with_for_update())
    if not admission: raise ValueError("ADMISSION_NOT_FOUND")
    if admission.status != "ADMITTED": raise ValueError("ADMISSION_NOT_ACTIVE")
    if not new_bed: raise ValueError("BED_NOT_FOUND")
    if new_bed.status != "AVAILABLE": raise ValueError("BED_NOT_AVAILABLE")
    old_assignment = db.scalar(select(BedAssignment).join(Bed).where(BedAssignment.admission_id == admission_id, BedAssignment.released_at.is_(None)).with_for_update())
    old_ward = old_bed = None
    if old_assignment:
        old_bed_obj = db.scalar(select(Bed).where(Bed.id == old_assignment.bed_id).with_for_update())
        if old_bed_obj:
            old_ward = db.scalar(select(Ward.name).where(Ward.id == old_bed_obj.ward_id))
            old_bed = old_bed_obj.bed_number
            old_assignment.released_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
            old_bed_obj.status = "AVAILABLE"
    new_assignment = BedAssignment(bed_id=new_bed.id, admission_id=admission_id, assigned_by=actor)
    db.add(new_assignment); new_bed.status = "OCCUPIED"
    new_ward = db.scalar(select(Ward.name).where(Ward.id == new_bed.ward_id))
    admission.ward = new_ward; admission.bed = new_bed.bed_number
    movement = PatientMovement(admission_id=admission_id, facility_id=facility_id, from_ward=old_ward, from_bed=old_bed, to_ward=new_ward, to_bed=new_bed.bed_number, reason=reason, moved_by=actor)
    db.add(movement)
    record_audit(db, action="PATIENT_WARD_TRANSFERRED", resource_type="PatientMovement", result="SUCCESS", user_id=actor, resource_id=str(movement.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(new_assignment); return new_assignment
