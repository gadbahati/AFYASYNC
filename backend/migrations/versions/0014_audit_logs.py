"""add audit logs

Revision ID: 0014_audit_logs
Revises: 0013_integration_facility_scope
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_audit_logs"
down_revision = "0013_integration_facility_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(120), nullable=True),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("device_id", sa.String(150), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, column in (
        ("ix_audit_logs_user_id", "user_id"),
        ("ix_audit_logs_facility_id", "facility_id"),
        ("ix_audit_logs_patient_id", "patient_id"),
        ("ix_audit_logs_action", "action"),
        ("ix_audit_logs_resource_type", "resource_type"),
        ("ix_audit_logs_result", "result"),
        ("ix_audit_logs_created_at", "created_at"),
    ):
        op.create_index(name, "audit_logs", [column])


def downgrade() -> None:
    for name in (
        "ix_audit_logs_created_at",
        "ix_audit_logs_result",
        "ix_audit_logs_resource_type",
        "ix_audit_logs_action",
        "ix_audit_logs_patient_id",
        "ix_audit_logs_facility_id",
        "ix_audit_logs_user_id",
    ):
        op.drop_index(name, table_name="audit_logs")
    op.drop_table("audit_logs")
