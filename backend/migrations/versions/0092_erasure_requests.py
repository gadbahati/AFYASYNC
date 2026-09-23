"""erasure requests for retention / DPA

Revision ID: 0092_erasure_requests
Revises: 0091_surveillance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0092_erasure_requests"
down_revision = "0091_surveillance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "erasure_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("request_type", sa.String(40), nullable=False, server_default="ERASURE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_erasure_requests_person_id", "erasure_requests", ["person_id"])
    op.create_index("ix_erasure_requests_facility_id", "erasure_requests", ["facility_id"])
    op.create_index("ix_erasure_person_status", "erasure_requests", ["person_id", "status"])
    op.create_index("ix_erasure_status", "erasure_requests", ["status"])


def downgrade() -> None:
    op.drop_table("erasure_requests")
