"""Migrations de schéma (Alembic) pour TOUS les schémas : public (maître + pharmacie historique) et chaque t_<slug>.

Règles :
- schéma sans table de version  → create_all (tables manquantes) puis stamp head (considéré à jour) ;
- schéma déjà versionné         → alembic upgrade head (migrations hand-written/autogénérées dans migrations/*/versions).
Nouvelle migration : python scripts/make_migration.py tenant|master "message"
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from database.base import Base
import database.models_master  # noqa: F401
import database.models_tenant  # noqa: F401
from database.config import db_manager

logger = logging.getLogger(__name__)
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "migrations")


def _config(kind: str, connection, schema: str) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", os.path.join(MIGRATIONS_DIR, kind))
    cfg.attributes["connection"] = connection
    cfg.attributes["schema"] = schema
    return cfg


def _base_engine():
    return db_manager._engines["supabase"] if "supabase" in db_manager._engines else db_manager._engines["master"]


def _has_version_table(connection, schema: str, table: str) -> bool:
    return bool(connection.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_schema = :s AND table_name = :t"
    ), {"s": schema, "t": table}).first())


def migrate_schema(kind: str, schema: str) -> str:
    """Applique les migrations `kind` ('tenant' | 'master') sur `schema`. Retourne l'action effectuée."""
    engine = _base_engine()
    version_table = "alembic_version_master" if kind == "master" else "alembic_version"
    with engine.connect() as connection:
        cfg = _config(kind, connection, schema)
        if not _has_version_table(connection, schema, version_table):
            command.stamp(cfg, "head")
            connection.commit()
            return "stamped"
        command.upgrade(cfg, "head")
        connection.commit()
        return "upgraded"


def ensure_tenant_schema(schema: str):
    """Crée les tables tenant manquantes dans `schema` puis applique/stampe les migrations tenant."""
    db_manager.create_schema_tables(schema)
    return migrate_schema("tenant", schema)


def migrate_all(include_tenants: bool = True) -> dict:
    """Met à jour public (maître + tenant) et tous les schémas de pharmacies. Idempotent."""
    from database.models_master import Tenant
    engine = _base_engine()
    results = {}
    Base.metadata.create_all(engine, checkfirst=True)  # tables maîtres + tenant dans public
    results["public/master"] = migrate_schema("master", "public")
    results["public/tenant"] = migrate_schema("tenant", "public")
    if include_tenants:
        with db_manager.get_master_session() as session:
            schemas = sorted({t.database_name for t in session.query(Tenant).all() if t.database_name and t.database_name != "public"})
        for schema in schemas:
            try:
                results[schema] = ensure_tenant_schema(schema)
            except Exception as e:
                logger.error(f"Migration {schema} échouée : {e}")
                results[schema] = f"error: {e}"
    logger.info(f"Migrations BD : {results}")
    return results


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
    for k, v in migrate_all().items():
        print(f"{k:28} {v}")
    sys.exit(0)
