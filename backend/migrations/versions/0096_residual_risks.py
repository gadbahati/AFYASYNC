"""residual risk register

Revision ID: 0096_residual_risks
Revises: 0095_change_control
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0096_residual_risks"
down_revision = "0095_change_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "residual_risks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(40), nullable=False, server_default="SECURITY"),
        sa.Column("inherent_level", sa.String(20), nullable=False, server_default="HIGH"),
        sa.Column("residual_level", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("controls", sa.Text(), nullable=True),
        sa.Column("owner", sa.String(120), nullable=True),
        sa.Column("treatment", sa.String(40), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    op.drop_table("residual_risks")
