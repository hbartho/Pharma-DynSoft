"""Réinitialisation des données d'exploitation d'une pharmacie (schéma tenant), avec sauvegarde en base."""
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import text

from database.config import db_manager

# Ordre respectant les clés étrangères
PURGE_TABLES = [
    "promo_code_usages", "discount_history", "price_history",
    "inventory_items", "inventory_sessions",
    "sale_returns", "debts", "supplier_debts",
    "sale_items", "pending_sales", "sales",
    "stock_movements", "supply_items", "supplies",
    "prescriptions", "shifts", "shift_schedules",
]
KEPT_TABLES = ["users", "categories", "units", "products", "customers", "suppliers", "settings", "promo_codes", "discount_rules"]
BACKUP_PREFIX = "bkp_"


def _engine():
    return db_manager.get_tenant_engine("pharmacie_centrale")


def _existing_tables(conn, schema: str) -> set:
    return {r[0] for r in conn.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = :s"), {"s": schema})}


def backup_schema_in_db(conn, schema: str) -> str:
    """Copie les tables purgées (+ produits/promo/paramètres) dans un schéma de sauvegarde horodaté."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bkp = f"{BACKUP_PREFIX}{schema}_{stamp}"
    conn.execute(text(f'CREATE SCHEMA "{bkp}"'))
    existing = _existing_tables(conn, schema)
    for table in PURGE_TABLES + ["products", "promo_codes", "settings"]:
        if table in existing:
            conn.execute(text(f'CREATE TABLE "{bkp}"."{table}" AS SELECT * FROM "{schema}"."{table}"'))
    return bkp


def reset_tenant_data(schema: str, backup: bool = True) -> Dict:
    """Purge les données d'exploitation, stock → 0, compteurs promo → 0. Transaction unique."""
    deleted: Dict[str, int] = {}
    with _engine().begin() as conn:
        backup_name = backup_schema_in_db(conn, schema) if backup else None
        existing = _existing_tables(conn, schema)
        for table in PURGE_TABLES:
            if table in existing:
                deleted[table] = conn.execute(text(f'DELETE FROM "{schema}"."{table}"')).rowcount
        products = conn.execute(text(f'UPDATE "{schema}".products SET stock = 0')).rowcount
        if "promo_codes" in existing:
            conn.execute(text(f'UPDATE "{schema}".promo_codes SET current_uses = 0'))
    return {
        "schema": schema,
        "backup_schema": backup_name,
        "deleted": deleted,
        "deleted_total": sum(deleted.values()),
        "products_reset": products,
        "kept": KEPT_TABLES,
    }


def list_backups(schema: str) -> List[Dict]:
    prefix = f"{BACKUP_PREFIX}{schema}_"
    with _engine().connect() as conn:
        rows = conn.execute(text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE :p ORDER BY schema_name DESC"),
            {"p": prefix.replace("_", r"\_") + "%"}).fetchall()
        result = []
        for (name,) in rows:
            stamp = name[len(prefix):]
            try:
                created = datetime.strptime(stamp, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                created = None
            sizes = conn.execute(text(
                "SELECT COALESCE(SUM(pg_total_relation_size(quote_ident(table_schema) || '.' || quote_ident(table_name))), 0) "
                "FROM information_schema.tables WHERE table_schema = :s"), {"s": name}).scalar()
            result.append({"name": name, "created_at": created, "size_bytes": int(sizes or 0)})
        return result


def drop_backup(name: str) -> None:
    if not name.startswith(BACKUP_PREFIX) or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError("Nom de sauvegarde invalide")
    with _engine().begin() as conn:
        conn.execute(text(f'DROP SCHEMA "{name}" CASCADE'))
