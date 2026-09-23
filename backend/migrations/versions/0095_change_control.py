"""change requests and release records

Revision ID: 0095_change_control
Revises: 0094_disaster_recovery
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0095_change_control"
down_revision = "0094_disaster_recovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "change_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("change_type", sa.String(40), nullable=False, server_default="STANDARD"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "release_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("environment", sa.String(30), nullable=False, server_default="staging"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("change_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("change_requests.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deployed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("release_records")
    op.drop_table("change_requests")
