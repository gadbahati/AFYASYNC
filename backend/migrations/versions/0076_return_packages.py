"""overseas_return_packages

Revision ID: 0076_return_packages
Revises: 0075_ussd_sessions
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0076_return_packages"
down_revision: Union[str, None] = "0075_ussd_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "overseas_return_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("overseas_treatment_cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "facility_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("facilities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("discharge_summary", sa.Text(), nullable=False),
        sa.Column("procedures_performed", sa.Text(), nullable=False),
        sa.Column("medications_on_discharge", sa.Text(), nullable=False),
        sa.Column("complications", sa.Text(), nullable=True),
        sa.Column("foreign_report_refs", sa.Text(), nullable=True),
        sa.Column("follow_up_plan", sa.Text(), nullable=False),
        sa.Column(
            "follow_up_facility_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("facilities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recommended_follow_up_date", sa.Date(), nullable=True),
        sa.Column("rehab_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rehab_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "issued_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_overseas_return_packages_case_id", "overseas_return_packages", ["case_id"], unique=True)
    op.create_index("ix_overseas_return_packages_facility_id", "overseas_return_packages", ["facility_id"])
    op.create_index("ix_overseas_return_packages_patient_id", "overseas_return_packages", ["patient_id"])
    op.create_index("ix_overseas_return_packages_status", "overseas_return_packages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_overseas_return_packages_status", table_name="overseas_return_packages")
    op.drop_index("ix_overseas_return_packages_patient_id", table_name="overseas_return_packages")
    op.drop_index("ix_overseas_return_packages_facility_id", table_name="overseas_return_packages")
    op.drop_index("ix_overseas_return_packages_case_id", table_name="overseas_return_packages")
    op.drop_table("overseas_return_packages")
