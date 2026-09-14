from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import settings
from app.database import Base
from app.coverage import models as coverage_models
from app.facilities import models as facility_models
from app.patients import models as patient_models
from app.rbac import models as rbac_models

_ = patient_models, coverage_models, facility_models, rbac_models

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _ensure_alembic_version_capacity(connection) -> None:
    """Keep the Alembic version column large enough for long branch IDs.

    This project has accumulated several descriptive migration revision IDs
    longer than Alembic's default VARCHAR(32). On an existing database the
    version table may already be VARCHAR(32), so widening it here before
    running the migration graph prevents a valid migration from failing only
    when Alembic records its revision. The check is a no-op on a new database
    before the initial migration creates the table.
    """
    table_exists = connection.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = 'alembic_version'
            LIMIT 1
            """
        )
    ).scalar()
    if table_exists:
        connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(128)"
            )
        )


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_alembic_version_capacity(connection)
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
