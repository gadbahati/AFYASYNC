"""Phase 165: provenance-backed inbound HIE clinical imports."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0134_hie_clinical_imports"
down_revision = "0133_hie_inbound_mpi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hie_imported_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "inbound_document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hie_inbound_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "facility_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("facilities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "patient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("hie_nodes.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("remote_resource_id", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="IMPORTED"),
        sa.Column("purpose_of_use", sa.String(length=40), nullable=False),
        sa.Column("sensitivity", sa.String(length=30), nullable=False, server_default="NORMAL"),
        sa.Column("normalized_code", sa.String(length=100), nullable=True),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_provenance", postgresql.JSONB(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "imported_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "source_node_id",
            "resource_type",
            "remote_resource_id",
            name="uq_hie_imported_resource_remote",
        ),
    )
    op.create_index(
        "ix_hie_imported_resources_facility_id",
        "hie_imported_resources",
        ["facility_id"],
    )
    op.create_index(
        "ix_hie_imported_resources_patient_id",
        "hie_imported_resources",
        ["patient_id"],
    )
    op.create_index(
        "ix_hie_imported_resources_status",
        "hie_imported_resources",
        ["status"],
    )
    op.create_index(
        "ix_hie_imported_resources_effective_at",
        "hie_imported_resources",
        ["effective_at"],
    )
    op.create_index(
        "ix_hie_imported_resources_patient_effective",
        "hie_imported_resources",
        ["patient_id", "effective_at"],
    )
    op.create_index(
        "ix_hie_imported_resources_inbound",
        "hie_imported_resources",
        ["inbound_document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_hie_imported_resources_inbound", table_name="hie_imported_resources")
    op.drop_index("ix_hie_imported_resources_patient_effective", table_name="hie_imported_resources")
    op.drop_index("ix_hie_imported_resources_effective_at", table_name="hie_imported_resources")
    op.drop_index("ix_hie_imported_resources_status", table_name="hie_imported_resources")
    op.drop_index("ix_hie_imported_resources_patient_id", table_name="hie_imported_resources")
    op.drop_index("ix_hie_imported_resources_facility_id", table_name="hie_imported_resources")
    op.drop_table("hie_imported_resources")
