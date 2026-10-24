"""Réinitialise les données d'exploitation d'une pharmacie comme pour une nouvelle pharmacie.

Conservé : utilisateurs, produits (stock → 0), catégories, unités, fournisseurs, clients, paramètres, codes promo, règles.
Supprimé : ventes, appros, lots, mouvements, dettes, retours, inventaires, shifts, plannings, historiques.
Une copie des tables purgées est gardée dans un schéma bkp_<schema>_<horodatage>.

Usage : python scripts/reset_tenant_data.py --schema public --confirm RESET [--no-backup]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from services.tenant_reset import reset_tenant_data  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, help="public (pharmacie_centrale) ou t_<slug>")
    parser.add_argument("--confirm", required=True, help="Taper RESET pour confirmer")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()
    if args.confirm != "RESET":
        sys.exit("Confirmation manquante (--confirm RESET)")
    result = reset_tenant_data(args.schema, backup=not args.no_backup)
    print("Sauvegarde :", result["backup_schema"] or "aucune")
    for table, n in result["deleted"].items():
        print(f"  {table:22s} {n:>6} ligne(s) supprimée(s)")
    print(f"  products.stock -> 0  ({result['products_reset']} produits)")
    print("Réinitialisation terminée pour le schéma", args.schema)


if __name__ == "__main__":
    main()
