"""Add template_code to facility_messages for safe messaging

Revision ID: 0074_message_templates
Revises: 0073_continuity_cards
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0074_message_templates"
down_revision: Union[str, None] = "0073_continuity_cards"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "facility_messages",
        sa.Column("template_code", sa.String(length=60), nullable=True),
    )
    op.create_index(
        "ix_facility_messages_template_code",
        "facility_messages",
        ["template_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_facility_messages_template_code", table_name="facility_messages")
    op.drop_column("facility_messages", "template_code")
