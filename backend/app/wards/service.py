from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.admissions.models import Admission
from app.wards.models import Bed, BedAssignment, Ward


def create_ward(db: Session, facility_id: UUID, actor: UUID, name: str, ward_type: str):
    ward = Ward(facility_id=facility_id, name=name, ward_type=ward_type)
    db.add(ward)
    record_audit(db, action="WARD_CREATED", resource_type="Ward", result="SUCCESS", user_id=actor, resource_id=str(ward.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(ward); return ward


def create_bed(db: Session, facility_id: UUID, actor: UUID, ward_id: UUID, bed_number: str):
    ward = db.scalar(select(Ward).where(Ward.id == ward_id, Ward.facility_id == facility_id))
    if not ward: raise ValueError("WARD_NOT_FOUND")
    bed = Bed(ward_id=ward_id, bed_number=bed_number)
    db.add(bed)
    record_audit(db, action="BED_CREATED", resource_type="Bed", result="SUCCESS", user_id=actor, resource_id=str(bed.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(bed); return bed


def assign_bed(db: Session, facility_id: UUID, actor: UUID, bed_id: UUID, admission_id: UUID):
    bed = db.scalar(select(Bed).join(Ward).where(Bed.id == bed_id, Ward.facility_id == facility_id).with_for_update())
    admission = db.scalar(select(Admission).where(Admission.id == admission_id, Admission.facility_id == facility_id).with_for_update())
    if not bed: raise ValueError("BED_NOT_FOUND")
    if not admission: raise ValueError("ADMISSION_NOT_FOUND")
    if admission.status != "ADMITTED": raise ValueError("ADMISSION_NOT_ACTIVE")
    if bed.status != "AVAILABLE": raise ValueError("BED_NOT_AVAILABLE")
    active = db.scalar(select(BedAssignment.id).where(BedAssignment.bed_id == bed_id, BedAssignment.released_at.is_(None)))
    if active: raise ValueError("BED_NOT_AVAILABLE")
    assignment = BedAssignment(bed_id=bed_id, admission_id=admission_id, assigned_by=actor)
    db.add(assignment)
    bed.status = "OCCUPIED"
    admission.ward = db.scalar(select(Ward.name).where(Ward.id == bed.ward_id)) or admission.ward
    admission.bed = bed.bed_number
    record_audit(db, action="BED_ASSIGNED", resource_type="BedAssignment", result="SUCCESS", user_id=actor, resource_id=str(assignment.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(assignment); return assignment


def release_bed(db: Session, facility_id: UUID, actor: UUID, bed_id: UUID):
    bed = db.scalar(select(Bed).join(Ward).where(Bed.id == bed_id, Ward.facility_id == facility_id).with_for_update())
    if not bed: raise ValueError("BED_NOT_FOUND")
    assignment = db.scalar(select(BedAssignment).where(BedAssignment.bed_id == bed_id, BedAssignment.released_at.is_(None)).with_for_update())
    if not assignment: raise ValueError("BED_NOT_OCCUPIED")
    assignment.released_at = datetime.now(timezone.utc)
    bed.status = "AVAILABLE"
    record_audit(db, action="BED_RELEASED", resource_type="BedAssignment", result="SUCCESS", user_id=actor, resource_id=str(assignment.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(assignment); return assignment
