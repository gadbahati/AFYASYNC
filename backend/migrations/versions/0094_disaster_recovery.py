"""disaster recovery drills and backup verifications

Revision ID: 0094_disaster_recovery
Revises: 0093_partner_interests
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0094_disaster_recovery"
down_revision = "0093_partner_interests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backup_verifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(80), nullable=False, server_default="POSTGRES"),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECORDED"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "dr_drills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("drill_type", sa.String(40), nullable=False, server_default="TABLETOP"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PLANNED"),
        sa.Column("scenario", sa.String(500), nullable=False),
        sa.Column("outcome_notes", sa.Text(), nullable=True),
        sa.Column("rto_minutes_target", sa.Integer(), nullable=True),
        sa.Column("rpo_minutes_target", sa.Integer(), nullable=True),
        sa.Column("conducted_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dr_drills")
    op.drop_table("backup_verifications")
