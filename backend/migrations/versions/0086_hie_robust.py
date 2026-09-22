"""hie robust tables

Revision ID: 0086_hie_robust
Revises: 0085_hie_export_logs
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0086_hie_robust"
down_revision = "0085_hie_export_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hie_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("node_type", sa.String(40), nullable=False, server_default="FACILITY"),
        sa.Column("endpoint_url", sa.String(500)),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("trust_level", sa.String(20), nullable=False, server_default="STANDARD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_hie_nodes_code"),
    )
    op.create_index("ix_hie_nodes_code", "hie_nodes", ["code"])
    op.create_index("ix_hie_nodes_status", "hie_nodes", ["status"])

    op.create_table(
        "hie_inbound_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL")),
        sa.Column("source_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hie_nodes.id", ondelete="SET NULL")),
        sa.Column("source_code", sa.String(80)),
        sa.Column("bundle_id", sa.String(80)),
        sa.Column("document_type", sa.String(50), nullable=False, server_default="UNKNOWN"),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("validation_status", sa.String(30), nullable=False, server_default="ACCEPTED"),
        sa.Column("validation_errors", postgresql.JSONB()),
        sa.Column("payload_meta", postgresql.JSONB()),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hie_inbound_documents_facility_id", "hie_inbound_documents", ["facility_id"])
    op.create_index("ix_hie_inbound_documents_patient_id", "hie_inbound_documents", ["patient_id"])
    op.create_index("ix_hie_inbound_documents_bundle_id", "hie_inbound_documents", ["bundle_id"])

    # Expand export logs if table exists from 0085
    op.add_column("hie_export_logs", sa.Column("purpose_of_use", sa.String(40)))
    op.add_column(
        "hie_export_logs",
        sa.Column("destination_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hie_nodes.id", ondelete="SET NULL")),
    )
    op.add_column(
        "hie_export_logs",
        sa.Column("redacted_sensitive", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("hie_export_logs", "redacted_sensitive")
    op.drop_column("hie_export_logs", "destination_node_id")
    op.drop_column("hie_export_logs", "purpose_of_use")
    op.drop_table("hie_inbound_documents")
    op.drop_table("hie_nodes")
