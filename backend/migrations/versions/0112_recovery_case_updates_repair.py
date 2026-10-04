"""repair missing recovery case update table
Revision ID: 0112_recovery_case_updates_repair
Revises: 0111_revenue_recovery
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0112_recovery_case_updates_repair"
down_revision = "0111_revenue_recovery"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("recovery_case_updates"):
        op.create_table(
            "recovery_case_updates",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "recovery_case_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("revenue_recovery_cases.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
            sa.Column("note", sa.Text()),
            sa.Column(
                "actor_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    index_names = {idx["name"] for idx in inspector.get_indexes("recovery_case_updates")}
    if "ix_recovery_case_updates_case" not in index_names:
        op.create_index(
            "ix_recovery_case_updates_case",
            "recovery_case_updates",
            ["recovery_case_id", "created_at"],
        )
def downgrade():
    op.drop_index("ix_recovery_case_updates_case", table_name="recovery_case_updates")
    op.drop_table("recovery_case_updates")
