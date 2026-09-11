"""add pharmacy tables

Revision ID: 0008
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007_laboratory"
branch_labels = None
depends_on = None


def _uuid():
    return sa.Column(postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table("medications",
        _uuid(), sa.Column("code", sa.String(50), nullable=False), sa.Column("name", sa.String(200), nullable=False),
        sa.Column("generic_name", sa.String(200)), sa.Column("strength", sa.String(100)), sa.Column("form", sa.String(100)),
        sa.Column("unit", sa.String(50)), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("code"))
    op.create_index("ix_medications_code", "medications", ["code"], unique=False)
    op.create_table("prescriptions",
        _uuid(), sa.Column("prescription_id", sa.String(60), nullable=False), sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("prescribed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["prescribed_by"], ["staff.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("prescription_id"))
    op.create_index("ix_prescriptions_prescription_id", "prescriptions", ["prescription_id"], unique=False)
    op.create_index("ix_prescriptions_encounter_id", "prescriptions", ["encounter_id"], unique=False)
    op.create_index("ix_prescriptions_patient_id", "prescriptions", ["patient_id"], unique=False)
    op.create_index("ix_prescriptions_status", "prescriptions", ["status"], unique=False)
    op.create_table("prescription_items",
        _uuid(), sa.Column("prescription_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("medication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dose", sa.String(100), nullable=False), sa.Column("frequency", sa.String(100), nullable=False), sa.Column("duration", sa.String(100), nullable=False),
        sa.Column("route", sa.String(100)), sa.Column("quantity", sa.Numeric(12, 2), nullable=False), sa.Column("instructions", sa.Text),
        sa.ForeignKeyConstraint(["prescription_id"], ["prescriptions.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_prescription_items_prescription_id", "prescription_items", ["prescription_id"], unique=False)
    op.create_table("medication_actions",
        _uuid(), sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("prescription_item_id", postgresql.UUID(as_uuid=True)),
        sa.Column("medication_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False), sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("notes", sa.Text),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["prescription_item_id"], ["prescription_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["performed_by"], ["staff.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_medication_actions_encounter_id", "medication_actions", ["encounter_id"], unique=False)
    op.create_table("inventory_items",
        _uuid(), sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("medication_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"), sa.Column("minimum_quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["medication_id"], ["medications.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("facility_id", "medication_id", name="uq_inventory_facility_medication"))
    op.create_index("ix_inventory_items_facility_id", "inventory_items", ["facility_id"], unique=False)
    op.create_index("ix_inventory_items_medication_id", "inventory_items", ["medication_id"], unique=False)
    op.create_table("inventory_batches",
        _uuid(), sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("batch_number", sa.String(100), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False), sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("purchase_price", sa.Numeric(12, 2), nullable=False), sa.Column("selling_price", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_inventory_batches_inventory_item_id", "inventory_batches", ["inventory_item_id"], unique=False)
    op.create_table("stock_movements",
        _uuid(), sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("batch_id", postgresql.UUID(as_uuid=True)),
        sa.Column("movement_type", sa.String(40), nullable=False), sa.Column("quantity", sa.Numeric(12, 2), nullable=False), sa.Column("reference_type", sa.String(50)),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True)), sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["inventory_item_id"], ["inventory_items.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["batch_id"], ["inventory_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["performed_by"], ["staff.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_stock_movements_inventory_item_id", "stock_movements", ["inventory_item_id"], unique=False)


def downgrade() -> None:
    op.drop_table("stock_movements")
    op.drop_table("inventory_batches")
    op.drop_table("inventory_items")
    op.drop_table("medication_actions")
    op.drop_table("prescription_items")
    op.drop_index("ix_prescriptions_status", table_name="prescriptions")
    op.drop_index("ix_prescriptions_patient_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_encounter_id", table_name="prescriptions")
    op.drop_index("ix_prescriptions_prescription_id", table_name="prescriptions")
    op.drop_table("prescriptions")
    op.drop_index("ix_medications_code", table_name="medications")
    op.drop_table("medications")
