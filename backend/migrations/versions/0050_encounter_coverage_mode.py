"""encounter coverage_mode and coverage_id

Revision ID: 0050_encounter_coverage_mode
Revises: 0045_merge_heads
Create Date: 2026-09-13

Adds multi-coverage fields so encounters can run as AFYASYNC, SHA, CASH, or OTHER
without redesigning the hospital OS.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0050_encounter_coverage_mode"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Best-effort additive migration; safe if columns already exist via create_all.
    conn = op.get_bind()
    insp = sa.inspect(conn)
    cols = {c["name"] for c in insp.get_columns("encounters")} if insp.has_table("encounters") else set()
    if "coverage_mode" not in cols:
        op.add_column(
            "encounters",
            sa.Column("coverage_mode", sa.String(length=20), nullable=False, server_default="CASH"),
        )
        op.create_index("ix_encounters_coverage_mode", "encounters", ["coverage_mode"])
    if "coverage_id" not in cols:
        op.add_column(
            "encounters",
            sa.Column("coverage_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_index("ix_encounters_coverage_id", "encounters", ["coverage_id"])
        try:
            op.create_foreign_key(
                "fk_encounters_coverage_id_coverage",
                "encounters",
                "coverage",
                ["coverage_id"],
                ["id"],
                ondelete="SET NULL",
            )
        except Exception:
            pass


def downgrade() -> None:
    try:
        op.drop_constraint("fk_encounters_coverage_id_coverage", "encounters", type_="foreignkey")
    except Exception:
        pass
    try:
        op.drop_index("ix_encounters_coverage_id", table_name="encounters")
    except Exception:
        pass
    try:
        op.drop_index("ix_encounters_coverage_mode", table_name="encounters")
    except Exception:
        pass
    try:
        op.drop_column("encounters", "coverage_id")
    except Exception:
        pass
    try:
        op.drop_column("encounters", "coverage_mode")
    except Exception:
        pass
