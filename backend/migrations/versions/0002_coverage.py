"""Add payer, payer plan and coverage tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_coverage"
down_revision = "0001_initial_patient_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("payer_type", sa.String(length=50), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("integration_status", sa.String(length=30), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_payers_code", "payers", ["code"])

    op.create_table(
        "payer_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payer_plans_payer_id", "payer_plans", ["payer_id"])

    op.create_table(
        "coverage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("membership_number", sa.String(length=100), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_plan_id"], ["payer_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coverage_person_id", "coverage", ["person_id"])
    op.create_index("ix_coverage_payer_id", "coverage", ["payer_id"])
    op.create_index("ix_coverage_payer_plan_id", "coverage", ["payer_plan_id"])


def downgrade() -> None:
    op.drop_index("ix_coverage_payer_plan_id", table_name="coverage")
    op.drop_index("ix_coverage_payer_id", table_name="coverage")
    op.drop_index("ix_coverage_person_id", table_name="coverage")
    op.drop_table("coverage")
    op.drop_index("ix_payer_plans_payer_id", table_name="payer_plans")
    op.drop_table("payer_plans")
    op.drop_index("ix_payers_code", table_name="payers")
    op.drop_table("payers")
