"""add facilities and departments

Revision ID: 0003_facilities_departments
Revises: 0002_coverage
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_facilities_departments"
down_revision = "0002_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("facility_type", sa.String(length=50), nullable=False),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("license_number", sa.String(length=100), nullable=True),
        sa.Column("county", sa.String(length=100), nullable=True),
        sa.Column("sub_county", sa.String(length=100), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("facility_id"),
    )
    op.create_index("ix_facilities_facility_id", "facilities", ["facility_id"])
    op.create_index("ix_facilities_status", "facilities", ["status"])

    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_departments_facility_id", "departments", ["facility_id"])
    op.create_index("ix_departments_status", "departments", ["status"])


def downgrade() -> None:
    op.drop_index("ix_departments_status", table_name="departments")
    op.drop_index("ix_departments_facility_id", table_name="departments")
    op.drop_table("departments")
    op.drop_index("ix_facilities_status", table_name="facilities")
    op.drop_index("ix_facilities_facility_id", table_name="facilities")
    op.drop_table("facilities")
