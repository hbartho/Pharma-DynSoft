"""Env Alembic - tables TENANT (une exécution par schéma de pharmacie : public, t_<slug>...).
La connexion et le schéma cible sont fournis par scripts/migrate_db.py via config.attributes.
"""
from alembic import context
from sqlalchemy import text

from database.base import Base
import database.models_tenant  # noqa: F401

config = context.config
target_metadata = Base.metadata
TENANT_TABLES = {t.name for t in Base.metadata.sorted_tables if t.schema is None}


def include_object(obj, name, type_, reflected, compare_to):
    # Autogénération centrée sur tables/colonnes ; index et contraintes nommées : à écrire à la main si besoin
    if type_ == "table":
        return name in TENANT_TABLES or (not reflected and obj.schema is None)
    if type_ in ("index", "unique_constraint", "foreign_key_constraint"):
        return False
    return True


def include_name(name, type_, parent_names):
    if type_ == "table":
        return name in TENANT_TABLES
    return True


def run_migrations_online():
    connection = config.attributes["connection"]
    schema = config.attributes.get("schema", "public")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version",
        version_table_schema=schema,
        include_object=include_object,
        include_name=include_name,
        include_schemas=False,
        compare_type=False,
        compare_server_default=False,
    )
    with context.begin_transaction():
        # Le DDL non qualifié (ALTER TABLE categories ...) cible le schéma de la pharmacie, puis revient à la normale au commit
        connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
        context.run_migrations()


run_migrations_online()
