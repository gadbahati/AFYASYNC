"""Phase 164: inbound HIE payload persistence and MPI resolution state."""

from alembic import op
import sqlalchemy as sa

revision = "0133_hie_inbound_mpi"
down_revision = "0132_cross_facility_mpi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hie_inbound_documents", sa.Column("payload", sa.JSON(), nullable=True))
    op.add_column(
        "hie_inbound_documents",
        sa.Column("match_status", sa.String(length=30), nullable=False, server_default="UNRESOLVED"),
    )
    op.add_column("hie_inbound_documents", sa.Column("match_reasons", sa.JSON(), nullable=True))
    op.add_column("hie_inbound_documents", sa.Column("matched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_hie_inbound_documents_match_status",
        "hie_inbound_documents",
        ["match_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_hie_inbound_documents_match_status", table_name="hie_inbound_documents")
    op.drop_column("hie_inbound_documents", "matched_at")
    op.drop_column("hie_inbound_documents", "match_reasons")
    op.drop_column("hie_inbound_documents", "match_status")
    op.drop_column("hie_inbound_documents", "payload")
