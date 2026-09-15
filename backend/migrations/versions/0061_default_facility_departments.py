"""seed standard hospital departments for existing facilities

Revision ID: 0061_default_facility_departments
Revises: 0060_patient_registration_runtime_safety
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0061_default_facility_departments"
down_revision = "0060_patient_registration_runtime_safety"
branch_labels = None
depends_on = None

DEFAULT_DEPARTMENTS = (
    ("REG", "Registration & Records"), ("OPD", "Outpatient Department"),
    ("CAS", "Casualty / Emergency"), ("GENMED", "General Medicine"),
    ("PAEDS", "Paediatrics"), ("OBGYN", "Maternity & Obstetrics / Gynaecology"),
    ("SURG", "General Surgery"), ("ORTHO", "Orthopaedics"), ("DENT", "Dental"),
    ("ENT", "Ear, Nose & Throat"), ("EYE", "Ophthalmology"), ("DERM", "Dermatology"),
    ("PSYCH", "Mental Health / Psychiatry"), ("NCD", "Non-Communicable Diseases"),
    ("HIV", "HIV / ART Clinic"), ("TB", "Tuberculosis Clinic"),
    ("LAB", "Laboratory"), ("RAD", "Radiology & Imaging"), ("PHARM", "Pharmacy"),
    ("PHYSIO", "Physiotherapy & Rehabilitation"), ("NUTR", "Nutrition & Dietetics"),
    ("THEATRE", "Operating Theatre"), ("ICU", "Intensive Care Unit"),
    ("HDU", "High Dependency Unit"), ("WARD", "General Wards"),
    ("MORT", "Mortuary"), ("AMB", "Ambulance / Transport"),
)


def upgrade() -> None:
    connection = op.get_bind()
    departments = sa.table("departments", sa.column("id"), sa.column("facility_id"), sa.column("name"), sa.column("code"), sa.column("status"))
    facilities = sa.table("facilities", sa.column("id"))
    for (facility_id,) in connection.execute(sa.select(facilities.c.id)).fetchall():
        existing = {code for (code,) in connection.execute(sa.select(departments.c.code).where(departments.c.facility_id == facility_id)).fetchall()}
        rows = [{"id": uuid4(), "facility_id": facility_id, "name": name, "code": code, "status": "ACTIVE"} for code, name in DEFAULT_DEPARTMENTS if code not in existing]
        if rows:
            connection.execute(departments.insert(), rows)


def downgrade() -> None:
    departments = sa.table("departments", sa.column("code"))
    op.execute(sa.delete(departments).where(departments.c.code.in_([code for code, _ in DEFAULT_DEPARTMENTS])))
