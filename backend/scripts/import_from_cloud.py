"""Importe la pharmacie (schéma dédié + fiche pharmacie + annuaire des comptes) depuis le cloud DynSoft.
Usage : python scripts/import_from_cloud.py [--if-empty | --force]
  --if-empty : n'importe que si le schéma local est vide (démarrage automatique)
  --force    : remplace les données locales existantes
Variables : CLOUD_SYNC_URL, CLOUD_SYNC_SLUG, CLOUD_SYNC_TOKEN, TENANT_SCHEMA, DATABASE_URL.
"""
import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main():
    args = set(sys.argv[1:])
    from services.cloud_import import import_from_cloud
    try:
        result = import_from_cloud(force="--force" in args)
    except Exception as e:
        print(f"ECHEC import cloud : {e}")
        sys.exit(0 if "--if-empty" in args else 1)
    if result.get("skipped"):
        print(f"Import ignoré : {result['reason']}")
        return
    print(f"Import terminé : {result['rows']} lignes dans {result['schema']}, {result['users']} compte(s) utilisateur")
    for table, n in sorted(result["counts"].items()):
        print(f"  {table:24} {n}")


if __name__ == "__main__":
    main()
