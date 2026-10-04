"""Phase 166: durable outbound HIE delivery queue."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0135_hie_delivery_queue"
down_revision = "0134_hie_clinical_imports"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "hie_delivery_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hie_nodes.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("export_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hie_export_logs.id", ondelete="SET NULL")),
        sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True),
        sa.Column("delivery_type", sa.String(50), nullable=False, server_default="FHIR_BUNDLE"),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_http_status", sa.Integer()),
        sa.Column("last_error", sa.Text()),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("destination_node_id", "idempotency_key", name="uq_hie_delivery_destination_key"),
    )
    for name, cols in [
        ("ix_hie_delivery_jobs_facility_id", ["facility_id"]),
        ("ix_hie_delivery_jobs_patient_id", ["patient_id"]),
        ("ix_hie_delivery_jobs_destination_node_id", ["destination_node_id"]),
        ("ix_hie_delivery_jobs_status", ["status"]),
        ("ix_hie_delivery_jobs_next_attempt_at", ["next_attempt_at"]),
    ]:
        op.create_index(name, "hie_delivery_jobs", cols)

def downgrade() -> None:
    for name in ["ix_hie_delivery_jobs_next_attempt_at","ix_hie_delivery_jobs_status","ix_hie_delivery_jobs_destination_node_id","ix_hie_delivery_jobs_patient_id","ix_hie_delivery_jobs_facility_id"]:
        op.drop_index(name, table_name="hie_delivery_jobs")
    op.drop_table("hie_delivery_jobs")
