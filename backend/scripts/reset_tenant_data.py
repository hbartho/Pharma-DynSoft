"""Réinitialise les données d'exploitation d'une pharmacie (schéma tenant) comme pour une nouvelle pharmacie.

Conservé : utilisateurs, produits (stock remis à 0), catégories, unités, fournisseurs, clients (dettes effacées),
paramètres (règles), codes promo, règles de rabais.
Supprimé : ventes, approvisionnements, lots, mouvements, dettes clients/fournisseurs, retours, inventaires,
shifts, plannings, ventes en attente, ordonnances, historiques de prix / rabais / usages promo.

Usage : python scripts/reset_tenant_data.py --schema public --confirm RESET
Une sauvegarde pg_dump du schéma est écrite dans /app/backups avant toute suppression.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import create_engine, text  # noqa: E402
from database.config import SUPABASE_URL  # noqa: E402

PURGE_TABLES = [
    "promo_code_usages", "discount_history", "price_history",
    "inventory_items", "inventory_sessions",
    "sale_returns", "debts", "supplier_debts",
    "sale_items", "pending_sales", "sales",
    "stock_movements", "supply_items", "supplies",
    "prescriptions", "shifts", "shift_schedules",
]


def backup_schema(url: str, schema: str) -> str:
    out_dir = Path("/app/backups")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"{schema}_avant_reset_{stamp}.dump"
    res = subprocess.run(["pg_dump", "--format=custom", "--schema", schema, "--file", str(out), url],
                         capture_output=True, text=True)
    if res.returncode == 0:
        return str(out)
    # pg_dump indisponible/incompatible : copie des tables purgées dans un schéma de sauvegarde en base
    bkp = f"bkp_{schema}_{stamp}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{bkp}"'))
        existing = {r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :s"), {"s": schema})}
        for table in PURGE_TABLES + ["products", "promo_codes", "settings"]:
            if table in existing:
                conn.execute(text(f'CREATE TABLE "{bkp}"."{table}" AS SELECT * FROM "{schema}"."{table}"'))
    return f"schéma de sauvegarde en base : {bkp} (pg_dump indisponible : {res.stderr.strip().splitlines()[-1] if res.stderr else 'erreur'})"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True, help="public (pharmacie_centrale) ou t_<slug>")
    parser.add_argument("--confirm", required=True, help="Taper RESET pour confirmer")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()
    if args.confirm != "RESET":
        sys.exit("Confirmation manquante (--confirm RESET)")
    url = SUPABASE_URL
    if not url:
        sys.exit("SUPABASE_URL / DATABASE_URL non configurée")

    if not args.no_backup:
        print("Sauvegarde :", backup_schema(url, args.schema))

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(f'SET search_path TO "{args.schema}", public'))
        existing = {r[0] for r in conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = :s"), {"s": args.schema})}
        for table in PURGE_TABLES:
            if table in existing:
                n = conn.execute(text(f'DELETE FROM "{args.schema}"."{table}"')).rowcount
                print(f"  {table:22s} {n:>6} ligne(s) supprimée(s)")
        n = conn.execute(text(f'UPDATE "{args.schema}".products SET stock = 0')).rowcount
        print(f"  products.stock -> 0  ({n} produits)")
        if "promo_codes" in existing:
            conn.execute(text(f'UPDATE "{args.schema}".promo_codes SET current_uses = 0'))
            print("  promo_codes.current_uses -> 0")
        if "settings" in existing:
            conn.execute(text(f"DELETE FROM \"{args.schema}\".settings WHERE key LIKE 'last_sale_number%' OR key LIKE 'counter_%'"))
    print("Réinitialisation terminée pour le schéma", args.schema)


if __name__ == "__main__":
    main()
