"""Seed a representative set of SHA-approved overseas procedures.

The full official list has 36 procedures. This seed provides a working subset
so facilities can start using the Treat Abroad workflow immediately. The
catalogue can be extended later from the gazetted list.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.treat_abroad.models import ApprovedOverseasProcedure

SAMPLE_PROCEDURES = [
    {
        "code": "OTA-LIVER-TX",
        "name": "Liver transplant",
        "description": "Orthotopic liver transplantation",
        "justification": "Specialised transplant capacity and post-operative support not fully available in Kenya",
        "max_cover_kes": 500000,
    },
    {
        "code": "OTA-BMT",
        "name": "Bone marrow transplant",
        "description": "Allogeneic or autologous bone marrow / stem cell transplant",
        "justification": "Limited local capacity for complex haematopoietic stem cell transplantation",
        "max_cover_kes": 500000,
    },
    {
        "code": "OTA-PED-CARDIAC",
        "name": "Complex paediatric cardiac surgery",
        "description": "Complex congenital heart surgery in children",
        "justification": "Selected complex congenital procedures still require overseas specialist centres",
        "max_cover_kes": 500000,
    },
    {
        "code": "OTA-JOINT-COMPLEX",
        "name": "Complex joint reconstruction / replacement",
        "description": "Complex joint procedures not routinely available locally",
        "justification": "Specialised implants and expertise limited for selected complex reconstructions",
        "max_cover_kes": 500000,
    },
    {
        "code": "OTA-NEURO-COMPLEX",
        "name": "Complex neurosurgical procedure",
        "description": "Selected complex neurosurgical interventions",
        "justification": "Certain advanced neurosurgical procedures require overseas capacity",
        "max_cover_kes": 500000,
    },
]


def seed_approved_procedures(db: Session) -> list[ApprovedOverseasProcedure]:
    created: list[ApprovedOverseasProcedure] = []
    for item in SAMPLE_PROCEDURES:
        existing = db.scalar(
            select(ApprovedOverseasProcedure).where(
                ApprovedOverseasProcedure.code == item["code"]
            )
        )
        if existing is None:
            row = ApprovedOverseasProcedure(**item, is_active=True)
            db.add(row)
            created.append(row)
    if created:
        db.flush()
    return created
