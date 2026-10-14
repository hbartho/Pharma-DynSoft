"""Ajoute la colonne permissions à la table users de tous les schémas (public + tenants).
Usage: python scripts/add_permissions_column.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def main():
    from sqlalchemy import text
    from database.config import db_manager, USE_SUPABASE
    from database.models_master import Tenant

    engine = db_manager._engines["supabase"] if USE_SUPABASE else db_manager._engines["master"]

    schemas = ["public"]
    try:
        with db_manager.get_master_session() as session:
            for t in session.query(Tenant).all():
                if t.database_name and t.database_name != "public":
                    schemas.append(t.database_name)
    except Exception as e:
        print(f"Lecture tenants impossible: {e}")

    with engine.connect() as conn:
        for schema in schemas:
            try:
                conn.execute(text(f'ALTER TABLE "{schema}".users ADD COLUMN IF NOT EXISTS permissions JSON'))
                conn.commit()
                print(f"OK {schema}.users")
            except Exception as e:
                print(f"ERREUR {schema}: {e}")


if __name__ == "__main__":
    main()
