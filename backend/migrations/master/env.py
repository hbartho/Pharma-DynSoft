"""Env Alembic - tables MAÎTRES du schéma public (tenants, user_directory, sync_state...)."""
from alembic import context

from database.base import Base
import database.models_master  # noqa: F401
import database.models_tenant  # noqa: F401

config = context.config
target_metadata = Base.metadata
MASTER_TABLES = {t.name for t in Base.metadata.sorted_tables if t.schema == "public"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in MASTER_TABLES
    if type_ in ("index", "unique_constraint", "foreign_key_constraint"):
        return False
    return True


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name in (None, "public")
    if type_ == "table":
        return name in MASTER_TABLES
    return True


def run_migrations_online():
    connection = config.attributes["connection"]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version_master",
        version_table_schema="public",
        include_object=include_object,
        include_name=include_name,
        include_schemas=True,
        compare_type=False,
        compare_server_default=False,
    )
    with context.begin_transaction():
        context.run_migrations()


run_migrations_online()
