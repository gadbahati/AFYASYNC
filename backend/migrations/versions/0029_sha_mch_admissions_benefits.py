"""add SHA MCH and inpatient admissions benefit packages

Revision ID: 0029_sha_mch_admissions_benefits
Revises: 0029_merge_0028_heads
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0029_sha_mch_admissions_benefits"
down_revision = "0029_merge_0028_heads"
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
    op.create_table(
        "benefit_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_code", sa.String(length=50), nullable=False),
        sa.Column("package_code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_code"),
    )
    op.create_index("ix_benefit_packages_payer_code", "benefit_packages", ["payer_code"])
    op.create_index("ix_benefit_packages_package_code", "benefit_packages", ["package_code"])
    op.create_index("ix_benefit_packages_status", "benefit_packages", ["status"])

    bind = op.get_bind()
    table = sa.table(
        "benefit_packages",
        sa.column("id"), sa.column("payer_code"), sa.column("package_code"),
        sa.column("name"), sa.column("description"), sa.column("status"),
    )
    for package in PACKAGES:
        exists = bind.execute(sa.select(table.c.id).where(table.c.package_code == package["package_code"])).scalar()
        if exists is None:
            bind.execute(sa.insert(table).values(id=uuid4(), **package, status="ACTIVE"))


def downgrade() -> None:
    op.drop_index("ix_benefit_packages_status", table_name="benefit_packages")
    op.drop_index("ix_benefit_packages_package_code", table_name="benefit_packages")
    op.drop_index("ix_benefit_packages_payer_code", table_name="benefit_packages")
    op.drop_table("benefit_packages")
