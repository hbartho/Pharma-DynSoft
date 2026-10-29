"""Met les noms de produits existants en MAJUSCULES sans accent, dans tous les schémas de pharmacies.

Usage : python scripts/normalize_product_names.py [--dry-run]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import text  # noqa: E402
from database.config import db_manager  # noqa: E402
from services.text import normalize_product_name  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    engine = db_manager.get_tenant_engine("pharmacie_centrale")
    with engine.begin() as conn:
        schemas = ["public"] + [r[0] for r in conn.execute(text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 't\\_%' ESCAPE '\\'"))]
        for schema in schemas:
            has = conn.execute(text(
                "SELECT 1 FROM information_schema.tables WHERE table_schema=:s AND table_name='products'"), {"s": schema}).first()
            if not has:
                continue
            rows = conn.execute(text(f'SELECT id, name FROM "{schema}".products')).fetchall()
            taken = {name for _, name in rows}
            changed = skipped = 0
            for pid, name in rows:
                new = normalize_product_name(name)
                if not new or new == name:
                    continue
                if new in taken:
                    skipped += 1
                    print(f"   doublon ignoré : {name!r} -> {new!r} existe déjà")
                    continue
                taken.add(new)
                changed += 1
                if not args.dry_run:
                    conn.execute(text(f'UPDATE "{schema}".products SET name=:n WHERE id=:i'), {"n": new, "i": pid})
                    conn.execute(text(f'UPDATE "{schema}".supply_items SET product_name=:n WHERE product_id=:i'), {"n": new, "i": pid})
            print(f"{schema:28s} {len(rows):5d} produits, {changed:4d} renommés, {skipped} ignorés{' (simulation)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
