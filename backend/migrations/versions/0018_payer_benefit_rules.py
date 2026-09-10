"""add configurable payer benefit rules

Revision ID: 0018_payer_benefit_rules
Revises: 0017_pharmacy_permissions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0018_payer_benefit_rules"
down_revision = "0017_pharmacy_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payer_benefit_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("service_code", sa.String(80), nullable=True),
        sa.Column("service_type", sa.String(60), nullable=True),
        sa.Column("payer_percent", sa.Numeric(5, 2), nullable=False, server_default="100"),
        sa.Column("fixed_patient_copay", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("max_covered_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_plan_id"], ["payer_plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("payer_percent >= 0 AND payer_percent <= 100", name="ck_benefit_payer_percent"),
        sa.CheckConstraint("fixed_patient_copay >= 0", name="ck_benefit_copay_nonnegative"),
        sa.CheckConstraint("max_covered_amount IS NULL OR max_covered_amount >= 0", name="ck_benefit_max_nonnegative"),
        sa.CheckConstraint("service_code IS NOT NULL OR service_type IS NOT NULL", name="ck_benefit_scope_present"),
        sa.CheckConstraint("effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from", name="ck_benefit_dates"),
    )
    op.create_index("ix_payer_benefit_rules_payer_id", "payer_benefit_rules", ["payer_id"])
    op.create_index("ix_payer_benefit_rules_plan_id", "payer_benefit_rules", ["payer_plan_id"])
    op.create_index("ix_payer_benefit_rules_service_code", "payer_benefit_rules", ["service_code"])
    op.create_index("ix_payer_benefit_rules_service_type", "payer_benefit_rules", ["service_type"])
    op.create_index("ix_payer_benefit_rules_status", "payer_benefit_rules", ["status"])


def downgrade() -> None:
    for name in [
        "ix_payer_benefit_rules_status",
        "ix_payer_benefit_rules_service_type",
        "ix_payer_benefit_rules_service_code",
        "ix_payer_benefit_rules_plan_id",
        "ix_payer_benefit_rules_payer_id",
    ]:
        op.drop_index(name, table_name="payer_benefit_rules")
    op.drop_table("payer_benefit_rules")
