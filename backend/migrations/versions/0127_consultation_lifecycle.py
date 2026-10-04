"""Phase 129 — consultation lifecycle and clinical sign-off."""
from alembic import op
import sqlalchemy as sa

revision = "0127_consultation_lifecycle"
down_revision = "0126_triage"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("consultations", sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"))
    op.add_column("consultations", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("consultations", sa.Column("signed_by", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_consultations_signed_by_staff",
        "consultations",
        "staff",
        ["signed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_consultations_status", "consultations", ["status"])


def downgrade():
    op.drop_index("ix_consultations_status", table_name="consultations")
    op.drop_constraint("fk_consultations_signed_by_staff", "consultations", type_="foreignkey")
    op.drop_column("consultations", "signed_by")
    op.drop_column("consultations", "signed_at")
    op.drop_column("consultations", "status")
