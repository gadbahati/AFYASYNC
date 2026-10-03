"""Phase 119 multi-tenant national-scale control plane.

Revision ID: 0123_multi_tenant_control_plane
Revises: 0122_contract_compliance_guardrails
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0123_multi_tenant_control_plane"
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
    op.create_index("ix_organizations_code", "organizations", ["code"], unique=True)
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

    bind = op.get_bind()

    # Give every existing active facility a tenant boundary. This preserves the
    # existing facility-centric installation while creating an explicit tenant
    # control plane for future networks, counties and national operators.
    bind.execute(sa.text("""
        INSERT INTO organizations (id, code, name, organization_type, status, created_at, updated_at)
        SELECT gen_random_uuid(),
               'FACILITY:' || f.facility_id,
               f.name,
               'FACILITY',
               CASE WHEN f.status = 'ACTIVE' THEN 'ACTIVE' ELSE 'INACTIVE' END,
               now(), now()
        FROM facilities f
        WHERE NOT EXISTS (
            SELECT 1 FROM organizations o WHERE o.code = 'FACILITY:' || f.facility_id
        )
    """))

    bind.execute(sa.text("""
        INSERT INTO organization_facilities (organization_id, facility_id, status, created_at)
        SELECT o.id, f.id,
               CASE WHEN f.status = 'ACTIVE' THEN 'ACTIVE' ELSE 'INACTIVE' END,
               now()
        FROM facilities f
        JOIN organizations o ON o.code = 'FACILITY:' || f.facility_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM organization_facilities ofa
            WHERE ofa.organization_id = o.id AND ofa.facility_id = f.id
        )
    """))

    # Preserve all existing staff access by assigning users to their facility tenant.
    bind.execute(sa.text("""
        INSERT INTO organization_users (organization_id, user_id, access_level, status, created_at)
        SELECT DISTINCT o.id, u.id, 'MEMBER', 'ACTIVE', now()
        FROM staff s
        JOIN users u ON u.person_id = s.person_id
        JOIN organizations o ON o.code = (
            SELECT 'FACILITY:' || f.facility_id FROM facilities f WHERE f.id = s.facility_id
        )
        WHERE s.status = 'ACTIVE'
          AND u.status = 'ACTIVE'
        ON CONFLICT (organization_id, user_id) DO NOTHING
    """))

    # A platform tenant gives system administrators an explicit national control-plane
    # boundary without changing ordinary facility authorization.
    bind.execute(sa.text("""
        INSERT INTO organizations (id, code, name, organization_type, status, description, created_at, updated_at)
        SELECT gen_random_uuid(), 'PLATFORM:NATIONAL', 'AfyaSync National Platform',
               'NATIONAL', 'ACTIVE',
               'Platform control-plane tenant for explicitly authorized national operations.',
               now(), now()
        WHERE NOT EXISTS (
            SELECT 1 FROM organizations WHERE code = 'PLATFORM:NATIONAL'
        )
    """))

    bind.execute(sa.text("""
        INSERT INTO organization_users (organization_id, user_id, access_level, status, created_at)
        SELECT o.id, u.id, 'ADMIN', 'ACTIVE', now()
        FROM organizations o
        CROSS JOIN users u
        JOIN staff s ON s.person_id = u.person_id
        JOIN staff_roles sr ON sr.staff_id = s.id
        JOIN roles r ON r.id = sr.role_id
        WHERE o.code = 'PLATFORM:NATIONAL'
          AND r.name = 'System Administrator'
          AND u.status = 'ACTIVE'
        ON CONFLICT (organization_id, user_id) DO NOTHING
    """))

    # Dedicated tenant administration capability. System Administrators remain
    # privileged even if a deployment has not yet assigned this permission.
    bind.execute(sa.text("""
        INSERT INTO permissions (id, code, description)
        SELECT gen_random_uuid(), 'tenancy.admin',
               'Create and manage organizations, tenant membership and facility membership.'
        WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'tenancy.admin')
    """))
    bind.execute(sa.text("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'System Administrator'
          AND p.code = 'tenancy.admin'
        ON CONFLICT DO NOTHING
    """))


def downgrade():
    op.drop_index("ix_org_user_user", table_name="organization_users")
    op.drop_table("organization_users")
    op.drop_index("ix_org_facility_facility", table_name="organization_facilities")
    op.drop_table("organization_facilities")
    op.drop_index("ix_organizations_type_status", table_name="organizations")
    op.drop_index("ix_organizations_parent_status", table_name="organizations")
    op.drop_index("ix_organizations_code", table_name="organizations")
    op.drop_table("organizations")
