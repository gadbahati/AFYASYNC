"""continuity_cards for consent-aware QR wallet

Revision ID: 0073_continuity_cards
Revises: 0072_seed_overseas_procedures
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0073_continuity_cards"
down_revision: Union[str, None] = "0072_seed_overseas_procedures"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "continuity_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("token_prefix", sa.String(12), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verify_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_continuity_cards_person_id", "continuity_cards", ["person_id"])
    op.create_index("ix_continuity_cards_token_hash", "continuity_cards", ["token_hash"], unique=True)
    op.create_index("ix_continuity_cards_token_prefix", "continuity_cards", ["token_prefix"])
    op.create_index("ix_continuity_cards_person_active", "continuity_cards", ["person_id", "is_active"])


def downgrade() -> None:
    op.drop_index("ix_continuity_cards_person_active", table_name="continuity_cards")
    op.drop_index("ix_continuity_cards_token_prefix", table_name="continuity_cards")
    op.drop_index("ix_continuity_cards_token_hash", table_name="continuity_cards")
    op.drop_index("ix_continuity_cards_person_id", table_name="continuity_cards")
    op.drop_table("continuity_cards")
