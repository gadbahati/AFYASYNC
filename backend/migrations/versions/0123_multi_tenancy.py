"""multi tenant organization model

Revision ID: 0123_multi_tenancy
Revises: 0122_contract_compliance_guardrails
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0123_multi_tenancy"
down_revision = "0122_contract_compliance_guardrails"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(120), nullable=False, unique=True),
        sa.Column("name", sa.String(220), nullable=False),
        sa.Column("organization_type", sa.String(40), nullable=False, server_default="PROVIDER_NETWORK"),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_organizations_code", "organizations", ["code"])
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"])
    op.create_index("ix_organizations_status", "organizations", ["status"])
    op.create_index("ix_organizations_parent_status", "organizations", ["parent_id", "status"])
    op.create_index("ix_organizations_type_status", "organizations", ["organization_type", "status"])

    op.create_table(
        "organization_facilities",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "facility_id", name="uq_org_facility"),
    )
    op.create_index("ix_org_facility_facility", "organization_facilities", ["facility_id", "status"])

    op.create_table(
        "organization_users",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("access_level", sa.String(30), nullable=False, server_default="MEMBER"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_org_user_user", "organization_users", ["user_id", "status"])

def downgrade():
    op.drop_table("organization_users")
    op.drop_table("organization_facilities")
    op.drop_index("ix_organizations_type_status", table_name="organizations")
    op.drop_index("ix_organizations_parent_status", table_name="organizations")
    op.drop_index("ix_organizations_status", table_name="organizations")
    op.drop_index("ix_organizations_parent_id", table_name="organizations")
    op.drop_index("ix_organizations_code", table_name="organizations")
    op.drop_table("organizations")
