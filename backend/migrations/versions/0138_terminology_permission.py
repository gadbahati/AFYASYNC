"""Phase 172b: protect terminology administration with a dedicated permission."""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision="0138_terminology_permission"
down_revision="0137_terminology_registry"
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    permissions=sa.table("permissions",sa.column("id"),sa.column("code"),sa.column("description"))
    roles=sa.table("roles",sa.column("id"),sa.column("name"))
    rp=sa.table("role_permissions",sa.column("role_id"),sa.column("permission_id"))
    code="terminology.manage"
    pid=bind.execute(sa.select(permissions.c.id).where(permissions.c.code==code)).scalar()
    if pid is None:
        pid=uuid4()
        bind.execute(sa.insert(permissions).values(id=pid,code=code,description="Manage AfyaSync terminology concepts and mappings"))
    role_rows=bind.execute(sa.select(roles.c.id).where(roles.c.name.in_(["Hospital Administrator","System Administrator"]))).fetchall()
    for (rid,) in role_rows:
        if bind.execute(sa.select(rp.c.role_id).where(rp.c.role_id==rid,rp.c.permission_id==pid)).first() is None:
            bind.execute(sa.insert(rp).values(role_id=rid,permission_id=pid))

def downgrade():
    bind=op.get_bind()
    permissions=sa.table("permissions",sa.column("id"),sa.column("code"))
    rp=sa.table("role_permissions",sa.column("permission_id"))
    pid=bind.execute(sa.select(permissions.c.id).where(permissions.c.code=="terminology.manage")).scalar()
    if pid:
        bind.execute(sa.delete(rp).where(rp.c.permission_id==pid))
        bind.execute(sa.delete(permissions).where(permissions.c.id==pid))
