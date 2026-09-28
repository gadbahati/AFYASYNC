"""national health exchange message envelope
Revision ID: 0105_health_exchange
Revises: 0104_provider_network
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0105_health_exchange";down_revision="0104_provider_network";branch_labels=None;depends_on=None
def upgrade():
 op.create_table("health_exchange_messages",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("message_id",sa.String(100),nullable=False),sa.Column("message_type",sa.String(60),nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="SET NULL")),sa.Column("source_facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="SET NULL")),sa.Column("destination_facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="SET NULL")),sa.Column("correlation_id",sa.String(100)),sa.Column("schema_version",sa.String(30),nullable=False,server_default="1.0"),sa.Column("payload",postgresql.JSONB,nullable=False),sa.Column("status",sa.String(30),nullable=False,server_default="ACCEPTED"),sa.Column("error_code",sa.String(80)),sa.Column("error_message",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.Column("processed_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("message_id",name="uq_health_exchange_message_id"))
 op.create_index("ix_health_exchange_message_status","health_exchange_messages",["status","created_at"]);op.create_index("ix_health_exchange_patient","health_exchange_messages",["patient_id","created_at"]);op.create_index("ix_health_exchange_type","health_exchange_messages",["message_type","created_at"]);op.create_index("ix_health_exchange_messages_source_facility_id","health_exchange_messages",["source_facility_id"]);op.create_index("ix_health_exchange_messages_destination_facility_id","health_exchange_messages",["destination_facility_id"]);op.create_index("ix_health_exchange_messages_correlation_id","health_exchange_messages",["correlation_id"])
def downgrade():
 for n in ["ix_health_exchange_messages_correlation_id","ix_health_exchange_messages_destination_facility_id","ix_health_exchange_messages_source_facility_id","ix_health_exchange_type","ix_health_exchange_patient","ix_health_exchange_message_status"]:op.drop_index(n,table_name="health_exchange_messages")
 op.drop_table("health_exchange_messages")
