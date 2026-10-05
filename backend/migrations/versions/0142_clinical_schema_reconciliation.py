"""Reconcile runtime clinical ORM models with the persisted clinical schema.

Adds the lifecycle columns required by the current clinical-note API while
preserving the original SOAP-style columns created by the initial migration.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0142_clinical_schema_reconciliation"
down_revision = "0141_imaging_result_fields"
branch_labels = None
depends_on = None


def _columns(bind, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "clinical_notes")

    if "content" not in columns:
        op.add_column("clinical_notes", sa.Column("content", sa.Text(), nullable=True))
        # Preserve existing clinical content when the table originated from 0006.
        op.execute(sa.text("""
            UPDATE clinical_notes
            SET content = concat_ws(E'\n\n',
                NULLIF(subjective, ''),
                NULLIF(objective, ''),
                NULLIF(assessment, ''),
                NULLIF(plan, '')
            )
            WHERE content IS NULL
        """))

    columns = _columns(bind, "clinical_notes")
    if "status" not in columns:
        op.add_column("clinical_notes", sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"))
    if "signed_at" not in columns:
        op.add_column("clinical_notes", sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
    if "signed_by" not in columns:
        op.add_column("clinical_notes", sa.Column("signed_by", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            "fk_clinical_notes_signed_by_staff",
            "clinical_notes",
            "staff",
            ["signed_by"],
            ["id"],
            ondelete="SET NULL",
        )
    if "updated_at" not in columns:
        op.add_column(
            "clinical_notes",
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    inspector = sa.inspect(bind)
    if not any(i["name"] == "ix_clinical_notes_status" for i in inspector.get_indexes("clinical_notes")):
        op.create_index("ix_clinical_notes_status", "clinical_notes", ["status"])


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {i["name"] for i in sa.inspect(bind).get_indexes("clinical_notes")}
    if "ix_clinical_notes_status" in indexes:
        op.drop_index("ix_clinical_notes_status", table_name="clinical_notes")
    columns = _columns(bind, "clinical_notes")
    if "signed_by" in columns:
        try:
            op.drop_constraint("fk_clinical_notes_signed_by_staff", "clinical_notes", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("clinical_notes", "signed_by")
    for name in ("updated_at", "signed_at", "status", "content"):
        if name in _columns(bind, "clinical_notes"):
            op.drop_column("clinical_notes", name)
