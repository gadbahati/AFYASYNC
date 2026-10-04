"""Phase 169: patient-controlled HIE data-sharing consent."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0136_hie_consents"
down_revision="0135_hie_delivery_queue"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("hie_consents",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("recipient_node_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("hie_nodes.id",ondelete="SET NULL")),
        sa.Column("status",sa.String(30),nullable=False,server_default="ACTIVE"),
        sa.Column("decision",sa.String(20),nullable=False,server_default="PERMIT"),
        sa.Column("purpose",sa.String(100),nullable=False,server_default="HOPERAT"),
        sa.Column("scope",sa.String(50),nullable=False,server_default="HIE_SHARE"),
        sa.Column("period_start",sa.DateTime(timezone=True)),sa.Column("period_end",sa.DateTime(timezone=True)),
        sa.Column("source",sa.String(30),nullable=False,server_default="FACILITY"),
        sa.Column("evidence",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("fhir_resource",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("revoked_at",sa.DateTime(timezone=True)),
        sa.Column("created_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_hie_consents_patient_id","hie_consents",["patient_id"])
    op.create_index("ix_hie_consents_facility_id","hie_consents",["facility_id"])
    op.create_index("ix_hie_consents_recipient_node_id","hie_consents",["recipient_node_id"])
    op.create_index("ix_hie_consents_status","hie_consents",["status"])

def downgrade():
    for n in ["ix_hie_consents_status","ix_hie_consents_recipient_node_id","ix_hie_consents_facility_id","ix_hie_consents_patient_id"]: op.drop_index(n,table_name="hie_consents")
    op.drop_table("hie_consents")
