"""add SHA MCH and inpatient admissions benefit packages

Revision ID: 0029_sha_mch_admissions_benefits
Revises: 0028_reports_permission
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0029_sha_mch_admissions_benefits"
down_revision = "0028_reports_permission"
branch_labels = None
depends_on = None


PACKAGES = (
    {
        "payer_code": "SHA",
        "package_code": "SHA-08",
        "name": "Maternal and Child Health Services",
        "description": (
            "Under the Social Health Authority framework, Maternal and Child Health services "
            "provide comprehensive support spanning antenatal care, supervised deliveries, "
            "postnatal check-ups, and childhood immunizations to ensure family well-being "
            "across accredited facilities."
        ),
    },
    {
        "payer_code": "SHA",
        "package_code": "SHA-07",
        "name": "Hospital Admissions / Inpatient Services",
        "description": (
            "The hospital admissions benefit covers essential inpatient requirements including "
            "general ward accommodation, professional nursing care, necessary diagnostic tests, "
            "and pharmaceuticals during a patient stay, ensuring structured financial protection "
            "for both routine maternity needs and critical medical interventions."
        ),
    },
)


def upgrade() -> None:
    bind = op.get_bind()
    table = sa.table(
        "benefit_packages",
        sa.column("id"),
        sa.column("payer_code"),
        sa.column("package_code"),
        sa.column("name"),
        sa.column("description"),
        sa.column("status"),
    )

    for package in PACKAGES:
        exists = bind.execute(
            sa.select(table.c.id).where(table.c.package_code == package["package_code"])
        ).scalar()
        if exists is None:
            bind.execute(
                sa.insert(table).values(
                    id=uuid4(),
                    payer_code=package["payer_code"],
                    package_code=package["package_code"],
                    name=package["name"],
                    description=package["description"],
                    status="ACTIVE",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    table = sa.table("benefit_packages", sa.column("package_code"))
    bind.execute(
        sa.delete(table).where(
            table.c.package_code.in_([package["package_code"] for package in PACKAGES])
        )
    )
