"""ussd_pins and ussd_sessions

Revision ID: 0075_ussd_sessions
Revises: 0074_message_templates
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0075_ussd_sessions"
down_revision: Union[str, None] = "0074_message_templates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ussd_pins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pin_hash", sa.String(128), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ussd_pins_person_id", "ussd_pins", ["person_id"], unique=True)

    op.create_table(
        "ussd_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", sa.String(120), nullable=False),
        sa.Column("phone_e164", sa.String(20), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("state", sa.String(40), nullable=False, server_default="WELCOME"),
        sa.Column("authenticated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ussd_sessions_session_id", "ussd_sessions", ["session_id"], unique=True)
    op.create_index("ix_ussd_sessions_phone_e164", "ussd_sessions", ["phone_e164"])
    op.create_index("ix_ussd_sessions_person_id", "ussd_sessions", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_ussd_sessions_person_id", table_name="ussd_sessions")
    op.drop_index("ix_ussd_sessions_phone_e164", table_name="ussd_sessions")
    op.drop_index("ix_ussd_sessions_session_id", table_name="ussd_sessions")
    op.drop_table("ussd_sessions")
    op.drop_index("ix_ussd_pins_person_id", table_name="ussd_pins")
    op.drop_table("ussd_pins")
