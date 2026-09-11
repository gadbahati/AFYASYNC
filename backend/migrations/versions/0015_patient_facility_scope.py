"""add facility scope to patient records

Revision ID: 0015_patient_facility_scope
Revises: 0014_patient_create_permission
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_patient_facility_scope"
down_revision = "0014_patient_create_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_id", "facility_id", name="uq_patient_facility"),
    )
    op.create_index("ix_patient_facilities_patient_id", "patient_facilities", ["patient_id"])
    op.create_index("ix_patient_facilities_facility_id", "patient_facilities", ["facility_id"])
    op.create_index("ix_patient_facilities_status", "patient_facilities", ["status"])


def downgrade() -> None:
    op.drop_index("ix_patient_facilities_status", table_name="patient_facilities")
    op.drop_index("ix_patient_facilities_facility_id", table_name="patient_facilities")
    op.drop_index("ix_patient_facilities_patient_id", table_name="patient_facilities")
    op.drop_table("patient_facilities")
