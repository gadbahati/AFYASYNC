"""Phase 172: persisted terminology concepts and cross-system mappings."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0137_terminology_registry"
down_revision="0136_hie_consents"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "terminology_concepts",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("system",sa.String(500),nullable=False),
        sa.Column("version",sa.String(80)),
        sa.Column("code",sa.String(200),nullable=False),
        sa.Column("display",sa.String(500),nullable=False),
        sa.Column("definition",sa.Text()),
        sa.Column("status",sa.String(30),nullable=False,server_default="ACTIVE"),
        sa.Column("properties",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("source",sa.String(100),nullable=False,server_default="AFYASYNC"),
        sa.Column("created_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint("system","version","code",name="uq_terminology_system_version_code"),
    )
    op.create_index("ix_terminology_concepts_system","terminology_concepts",["system"])
    op.create_index("ix_terminology_concepts_status","terminology_concepts",["status"])
    op.create_table(
        "terminology_mappings",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("source_system",sa.String(500),nullable=False),
        sa.Column("source_code",sa.String(200),nullable=False),
        sa.Column("target_system",sa.String(500),nullable=False),
        sa.Column("target_code",sa.String(200),nullable=False),
        sa.Column("equivalence",sa.String(30),nullable=False,server_default="equivalent"),
        sa.Column("source_display",sa.String(500)),
        sa.Column("target_display",sa.String(500)),
        sa.Column("status",sa.String(30),nullable=False,server_default="ACTIVE"),
        sa.Column("provenance",postgresql.JSONB(),nullable=False,server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint("source_system","source_code","target_system","target_code",name="uq_terminology_mapping"),
    )
    op.create_index("ix_terminology_mappings_source_system","terminology_mappings",["source_system"])
    op.create_index("ix_terminology_mappings_target_system","terminology_mappings",["target_system"])
    op.create_index("ix_terminology_mappings_status","terminology_mappings",["status"])

def downgrade():
    for n,t in [
        ("ix_terminology_mappings_status","terminology_mappings"),
        ("ix_terminology_mappings_target_system","terminology_mappings"),
        ("ix_terminology_mappings_source_system","terminology_mappings"),
    ]: op.drop_index(n,table_name=t)
    op.drop_table("terminology_mappings")
    for n,t in [("ix_terminology_concepts_status","terminology_concepts"),("ix_terminology_concepts_system","terminology_concepts")]: op.drop_index(n,table_name=t)
    op.drop_table("terminology_concepts")
