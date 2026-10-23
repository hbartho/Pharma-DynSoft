"""Initialise une installation locale : tables du schéma public + super admin DynSoft.
Idempotent : peut être relancé à chaque démarrage du conteneur backend.
Variables : DATABASE_URL (ou SUPABASE_URL), SUPERADMIN_EMAIL, SUPERADMIN_PASSWORD.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def wait_for_db(engine, retries: int = 30):
    from sqlalchemy import text
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as e:
            print(f"Base non prête ({attempt}/{retries}) : {e.__class__.__name__}")
            time.sleep(2)
    raise SystemExit("Impossible de joindre PostgreSQL")


def main():
    from database.config import db_manager, USE_SUPABASE
    from database.base import Base
    import database.models_master  # noqa: F401
    import database.models_tenant  # noqa: F401
    from database.models_master import UserDirectory
    from database.directory import upsert_directory_entry
    from auth import hash_password

    if not USE_SUPABASE:
        raise SystemExit("DATABASE_URL manquant : le mode local requiert une URL PostgreSQL unique")

    from database.tenant_context import FORCED_SCHEMA
    from sqlalchemy import text

    engine = db_manager._engines["supabase"]
    wait_for_db(engine)
    Base.metadata.create_all(engine, checkfirst=True)
    print("Tables du schéma public OK")

    # Nouvelles tables éventuelles dans les schémas des pharmacies existantes
    from database.models_master import Tenant
    with db_manager.get_master_session() as session:
        schemas = [t.database_name for t in session.query(Tenant).all() if t.database_name and t.database_name != "public"]
    for schema in schemas:
        db_manager.create_schema_tables(schema)
    if schemas:
        print(f"Schémas pharmacies vérifiés : {', '.join(schemas)}")

    if FORCED_SCHEMA and FORCED_SCHEMA != "public":
        with engine.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{FORCED_SCHEMA}"'))
            conn.commit()
        tenant_tables = [t for t in Base.metadata.sorted_tables if t.schema is None]
        Base.metadata.create_all(engine.execution_options(schema_translate_map={None: FORCED_SCHEMA}),
                                 tables=tenant_tables, checkfirst=True)
        print(f"Serveur dédié : schéma {FORCED_SCHEMA} OK")

    with db_manager.get_master_session() as session:
        has_super_admin = session.query(UserDirectory).filter(
            UserDirectory.is_super_admin.is_(True)
        ).first() is not None

    if has_super_admin:
        print("Super admin déjà présent : aucun compte créé")
        return

    email = (os.environ.get("SUPERADMIN_EMAIL") or "").strip().lower()
    password = os.environ.get("SUPERADMIN_PASSWORD") or ""
    if not email or len(password) < 8:
        print("SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD (8 caractères min.) absents : super admin non créé")
        return

    if not upsert_directory_entry(email, tenant_slug=None, is_super_admin=True,
                                  password_hash=hash_password(password), name="DynSoft"):
        raise SystemExit("Echec de la création du super admin")
    print(f"Super admin créé : {email}")


if __name__ == "__main__":
    main()
