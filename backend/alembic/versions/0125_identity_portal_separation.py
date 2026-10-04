"""Phase 125.x — identity, portal and government separation.

Government access is an explicit identity binding. It is not granted by
operating-scope selection and it is independent from facility staff membership.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0125_identity_portal_separation"
down_revision = "0124_business_continuity"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("refresh_sessions", sa.Column("portal_type", sa.String(30), nullable=False, server_default="facility"))
    op.add_column("refresh_sessions", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_refresh_sessions_organization",
        "refresh_sessions",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_refresh_sessions_organization_id", "refresh_sessions", ["organization_id"])

    op.create_table(
        "government_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_code", sa.String(80), nullable=False),
        sa.Column("scope_level", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_gov_access_org_user"),
    )
    op.create_index("ix_gov_access_user_status", "government_access", ["user_id", "status"])
    op.create_index("ix_gov_access_org_status", "government_access", ["organization_id", "status"])


def downgrade():
    op.drop_index("ix_gov_access_org_status", table_name="government_access")
    op.drop_index("ix_gov_access_user_status", table_name="government_access")
    op.drop_table("government_access")
    op.drop_index("ix_refresh_sessions_organization_id", table_name="refresh_sessions")
    op.drop_constraint("fk_refresh_sessions_organization", "refresh_sessions", type_="foreignkey")
    op.drop_column("refresh_sessions", "organization_id")
    op.drop_column("refresh_sessions", "portal_type")
