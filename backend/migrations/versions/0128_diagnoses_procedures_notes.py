"""Phase 130 — diagnoses, procedures and clinical notes."""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0128_diagnoses_procedures_notes"
down_revision = "0127_consultation_lifecycle"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("clinical.procedure.write", "Record clinical procedures"),
    ("clinical.note.write", "Create and sign clinical notes"),
)

def upgrade():
    op.create_table(
        "clinical_procedures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("procedure_code", sa.String(50), nullable=True),
        sa.Column("procedure_name", sa.String(250), nullable=False),
        sa.Column("procedure_type", sa.String(40), nullable=False, server_default="CLINICAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["performed_by"], ["staff.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_clinical_procedures_encounter_performed_at", "clinical_procedures", ["encounter_id", "performed_at"])

    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_type", sa.String(40), nullable=False, server_default="PROGRESS"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["author_id"], ["staff.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["signed_by"], ["staff.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_clinical_notes_encounter_created_at", "clinical_notes", ["encounter_id", "created_at"])

    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    for code, description in PERMISSIONS:
        if bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar() is None:
            bind.execute(sa.insert(permissions).values(id=uuid4(), code=code, description=description))

    role_rows = bind.execute(sa.select(roles.c.id, roles.c.name).where(roles.c.name.in_(
        ["Doctor", "Nurse", "Hospital Administrator", "System Administrator"]
    ))).fetchall()
    grants = {
        "Doctor": {"clinical.procedure.write", "clinical.note.write"},
        "Nurse": {"clinical.procedure.write", "clinical.note.write"},
        "Hospital Administrator": {p[0] for p in PERMISSIONS},
        "System Administrator": {p[0] for p in PERMISSIONS},
    }
    for role in role_rows:
        for code in grants.get(role.name, set()):
            permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar_one()
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role.id,
                role_permissions.c.permission_id == permission_id,
            )).first()
            if exists is None:
                bind.execute(sa.insert(role_permissions).values(role_id=role.id, permission_id=permission_id))

def downgrade():
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    ids = [row[0] for row in bind.execute(sa.select(permissions.c.id).where(
        permissions.c.code.in_([p[0] for p in PERMISSIONS])
    )).fetchall()]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
    op.drop_index("ix_clinical_notes_encounter_created_at", table_name="clinical_notes")
    op.drop_table("clinical_notes")
    op.drop_index("ix_clinical_procedures_encounter_performed_at", table_name="clinical_procedures")
    op.drop_table("clinical_procedures")
