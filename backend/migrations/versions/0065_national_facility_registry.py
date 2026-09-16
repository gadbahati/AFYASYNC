"""add national facility registry metadata and history

Revision ID: 0065_national_facility_registry
Revises: 0064_billing_permissions
"""

from alembic import op
import sqlalchemy as sa

revision = "0065_national_facility_registry"
down_revision = "0064_billing_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "facility_registry_records",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="KMHFR"),
        sa.Column("source_id", sa.String(120), nullable=True),
        sa.Column("mfl_code", sa.String(50), nullable=True),
        sa.Column("keph_level", sa.String(20), nullable=True),
        sa.Column("ownership", sa.String(120), nullable=True),
        sa.Column("ward", sa.String(120), nullable=True),
        sa.Column("constituency", sa.String(120), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("services", sa.JSON(), nullable=True),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "source_id", name="uq_facility_registry_source_id"),
        sa.UniqueConstraint("source", "mfl_code", name="uq_facility_registry_mfl_code"),
    )
    op.create_index("ix_facility_registry_records_facility_id", "facility_registry_records", ["facility_id"])
    op.create_index("ix_facility_registry_records_mfl_code", "facility_registry_records", ["mfl_code"])
    op.create_index("ix_facility_registry_records_keph_level", "facility_registry_records", ["keph_level"])
    op.create_index("ix_facility_registry_records_ownership", "facility_registry_records", ["ownership"])
    op.create_index("ix_facility_registry_records_ward", "facility_registry_records", ["ward"])

    op.create_table(
        "facility_registry_history",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("facility_id", sa.UUID(), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("before_record", sa.JSON(), nullable=True),
        sa.Column("after_record", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_facility_registry_history_facility_id", "facility_registry_history", ["facility_id"])
    op.create_index("ix_facility_registry_history_occurred_at", "facility_registry_history", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_facility_registry_history_occurred_at", table_name="facility_registry_history")
    op.drop_index("ix_facility_registry_history_facility_id", table_name="facility_registry_history")
    op.drop_table("facility_registry_history")
    op.drop_index("ix_facility_registry_records_ward", table_name="facility_registry_records")
    op.drop_index("ix_facility_registry_records_ownership", table_name="facility_registry_records")
    op.drop_index("ix_facility_registry_records_keph_level", table_name="facility_registry_records")
    op.drop_index("ix_facility_registry_records_mfl_code", table_name="facility_registry_records")
    op.drop_index("ix_facility_registry_records_facility_id", table_name="facility_registry_records")
    op.drop_table("facility_registry_records")
