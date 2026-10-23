"""Génère une migration Alembic par comparaison modèles ↔ base de référence (.env).
Usage : python scripts/make_migration.py tenant|master "ajout colonne x" [--ref=t_slug]
Puis relire le fichier créé dans migrations/<kind>/versions/ avant de déployer.
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from alembic import command
from scripts.migrate_db import _config, _base_engine, migrate_schema


def main():
    if len(sys.argv) < 3 or sys.argv[1] not in ("tenant", "master"):
        raise SystemExit(__doc__)
    kind, message = sys.argv[1], " ".join(a for a in sys.argv[2:] if not a.startswith("--"))
    rev_id = datetime.now().strftime("%Y%m%d%H%M")
    engine = _base_engine()
    if kind == "master":
        migrate_schema("master", "public")  # la base de référence doit être à jour avant comparaison
        with engine.connect() as connection:
            command.revision(_config("master", connection, "public"), message=message, autogenerate=True, rev_id=rev_id)
    else:
        # Référence : un schéma de pharmacie créé par create_all (le schéma public historique contient du bruit manuel)
        from sqlalchemy import text
        ref = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--ref=")), None)
        if not ref:
            with engine.connect() as connection:
                row = connection.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 't\\_%' ORDER BY 1 LIMIT 1")).first()
            ref = row[0] if row else "public"
        migrate_schema("tenant", ref)
        print(f"Schéma de référence : {ref}")
        with engine.connect() as connection:
            command.revision(_config("tenant", connection, ref), message=message, autogenerate=True, rev_id=rev_id)
    print(f"Migration {kind} générée : migrations/{kind}/versions/{rev_id}_*.py — vérifiez son contenu.")


if __name__ == "__main__":
    main()
