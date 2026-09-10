"""add billing tables

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _uuid():
    return sa.Column(postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS afasync_invoice_seq START WITH 1 INCREMENT BY 1")
    op.create_table("services", _uuid(), sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("code", sa.String(80), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("department_id", postgresql.UUID(as_uuid=True)), sa.Column("service_type", sa.String(60), nullable=False), sa.Column("price", sa.Numeric(14, 2), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_services_facility_id", "services", ["facility_id"]); op.create_index("ix_services_status", "services", ["status"]); op.create_unique_constraint("uq_services_facility_code", "services", ["facility_id", "code"])
    op.create_table("charges", _uuid(), sa.Column("charge_id", sa.String(70), nullable=False), sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("quantity", sa.Numeric(12, 2), nullable=False), sa.Column("unit_price", sa.Numeric(14, 2), nullable=False), sa.Column("total_amount", sa.Numeric(14, 2), nullable=False), sa.Column("source_type", sa.String(50), nullable=False), sa.Column("source_id", postgresql.UUID(as_uuid=True)), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("charge_id"))
    for name, column in [("ix_charges_charge_id","charge_id"),("ix_charges_encounter_id","encounter_id"),("ix_charges_patient_id","patient_id"),("ix_charges_facility_id","facility_id"),("ix_charges_status","status")]: op.create_index(name,"charges",[column])
    op.create_table("invoices", _uuid(), sa.Column("invoice_id", sa.String(70), nullable=False), sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("subtotal", sa.Numeric(14,2), nullable=False), sa.Column("payer_amount", sa.Numeric(14,2), nullable=False, server_default="0"), sa.Column("patient_amount", sa.Numeric(14,2), nullable=False, server_default="0"), sa.Column("total_amount", sa.Numeric(14,2), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.ForeignKeyConstraint(["patient_id"],["persons.id"],ondelete="RESTRICT"), sa.ForeignKeyConstraint(["facility_id"],["facilities.id"],ondelete="RESTRICT"), sa.ForeignKeyConstraint(["encounter_id"],["encounters.id"],ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("invoice_id"))
    for name,column in [("ix_invoices_invoice_id","invoice_id"),("ix_invoices_patient_id","patient_id"),("ix_invoices_facility_id","facility_id"),("ix_invoices_encounter_id","encounter_id"),("ix_invoices_status","status")]: op.create_index(name,"invoices",[column])
    op.create_table("invoice_items", _uuid(), sa.Column("invoice_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("charge_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("description",sa.String(250),nullable=False),sa.Column("quantity",sa.Numeric(12,2),nullable=False),sa.Column("unit_price",sa.Numeric(14,2),nullable=False),sa.Column("amount",sa.Numeric(14,2),nullable=False),sa.ForeignKeyConstraint(["invoice_id"],["invoices.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["charge_id"],["charges.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id")); op.create_index("ix_invoice_items_invoice_id","invoice_items",["invoice_id"])
    op.create_table("payments", _uuid(), sa.Column("transaction_id",sa.String(80),nullable=False),sa.Column("invoice_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),nullable=False),sa.Column("amount",sa.Numeric(14,2),nullable=False),sa.Column("payment_method",sa.String(40),nullable=False),sa.Column("provider",sa.String(80)),sa.Column("external_reference",sa.String(150)),sa.Column("status",sa.String(30),nullable=False,server_default="CREATED"),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.text("now()")),sa.Column("confirmed_at",sa.DateTime(timezone=True)),sa.ForeignKeyConstraint(["invoice_id"],["invoices.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["patient_id"],["persons.id"],ondelete="RESTRICT"),sa.ForeignKeyConstraint(["facility_id"],["facilities.id"],ondelete="RESTRICT"),sa.PrimaryKeyConstraint("id"),sa.UniqueConstraint("transaction_id"))
    for name,column in [("ix_payments_transaction_id","transaction_id"),("ix_payments_invoice_id","invoice_id"),("ix_payments_patient_id","patient_id"),("ix_payments_facility_id","facility_id"),("ix_payments_status","status")]: op.create_index(name,"payments",[column])


def downgrade() -> None:
    op.drop_table("payments"); op.drop_index("ix_invoice_items_invoice_id",table_name="invoice_items"); op.drop_table("invoice_items"); op.drop_table("invoices"); op.drop_table("charges"); op.drop_index("ix_services_status",table_name="services"); op.drop_index("ix_services_facility_id",table_name="services"); op.drop_constraint("uq_services_facility_code","services",type_="unique"); op.drop_table("services"); op.execute("DROP SEQUENCE IF EXISTS afasync_invoice_seq")
