"""department capacity for appointment fairness

Revision ID: 0077_department_capacity
Revises: 0076_return_packages
Create Date: 2026-09-20
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0077_department_capacity"
down_revision = "0076_return_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "department_capacity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("max_appointments_per_day", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("slot_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("max_pending_requests", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("open_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("close_hour", sa.Integer(), nullable=False, server_default="17"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("facility_id", "department_id", name="uq_dept_capacity_facility_dept"),
    )
    op.create_index("ix_department_capacity_facility_id", "department_capacity", ["facility_id"])
    op.create_index("ix_department_capacity_department_id", "department_capacity", ["department_id"])


def downgrade() -> None:
    op.drop_table("department_capacity")
