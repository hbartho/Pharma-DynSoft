"""Import initial d'une pharmacie depuis le cloud DynSoft vers un serveur local dédié (TENANT_SCHEMA).
Télécharge l'export NDJSON (GET /api/cloud-sync/<slug>/export) et remplace le schéma local de la pharmacie.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import requests
from sqlalchemy import text, select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.config import db_manager
from database.models_master import Tenant, UserDirectory
from database.tenant_context import FORCED_SCHEMA, tenant_schema_name
from services import cloud_sync

logger = logging.getLogger(__name__)


def target_schema() -> str:
    return FORCED_SCHEMA or tenant_schema_name(cloud_sync.CLOUD_SYNC_SLUG)


def schema_has_data(schema: str) -> bool:
    users = cloud_sync.table_by_name("users")
    try:
        with db_manager.schema_engine(schema).connect() as conn:
            return (conn.execute(select(func.count()).select_from(users)).scalar() or 0) > 0
    except Exception:
        return False


def _upsert_master(conn, table, rows, conflict_col: str):
    for row in rows:
        values = cloud_sync.deserialize_row(table, row)
        stmt = pg_insert(table).values(**values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[table.c[conflict_col]],
            set_={c.name: stmt.excluded[c.name] for c in table.columns if c.name not in ("id", conflict_col)},
        )
        conn.execute(stmt)


def import_from_cloud(force: bool = False) -> Dict[str, Any]:
    if not cloud_sync.LOCAL_ENABLED:
        raise RuntimeError("CLOUD_SYNC_URL / CLOUD_SYNC_SLUG / CLOUD_SYNC_TOKEN requis")
    slug, schema = cloud_sync.CLOUD_SYNC_SLUG, target_schema()
    if schema == "public":
        raise RuntimeError("TENANT_SCHEMA doit désigner le schéma de la pharmacie (ex. t_noormin), pas public")
    if not force and schema_has_data(schema):
        return {"skipped": True, "reason": f"Le schéma {schema} contient déjà des données (utilisez --force pour remplacer)"}

    url = f"{cloud_sync.CLOUD_SYNC_URL}/api/cloud-sync/{slug}/export"
    logger.info(f"Import cloud → {schema} depuis {url}")
    staging = f"{schema}__import"
    base = db_manager.schema_engine("public")
    with base.connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{staging}" CASCADE'))
        conn.commit()
    db_manager.create_schema_tables(staging)
    stg_engine = db_manager.schema_engine(staging)

    counts: Dict[str, int] = {}
    master_rows: Dict[str, list] = {}
    meta: Dict[str, Any] = {}
    done = False
    with requests.get(url, headers={"X-Sync-Token": cloud_sync.CLOUD_SYNC_TOKEN}, stream=True, timeout=(30, 600)) as r:
        if r.status_code >= 400:
            raise RuntimeError(f"Cloud {r.status_code}: {r.text[:200]}")
        with stg_engine.begin() as conn:
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                msg = json.loads(line)
                if "meta" in msg:
                    meta = msg["meta"]
                elif "master" in msg:
                    master_rows[msg["master"]] = msg["rows"]
                elif "table" in msg:
                    table = cloud_sync.table_by_name(msg["table"])
                    if table is None or not msg["rows"]:
                        continue
                    values = [cloud_sync.deserialize_row(table, row) for row in msg["rows"]]
                    for i in range(0, len(values), 200):
                        conn.execute(pg_insert(table).values(values[i:i + 200]))
                    counts[table.name] = counts.get(table.name, 0) + len(values)
                elif msg.get("done"):
                    done = True
    if not done:
        with base.connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{staging}" CASCADE'))
            conn.commit()
        raise RuntimeError("Export cloud incomplet (connexion interrompue) : import annulé")

    with base.connect() as conn:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        conn.execute(text(f'ALTER SCHEMA "{staging}" RENAME TO "{schema}"'))
        conn.commit()
    db_manager._schema_session_factories.pop(schema, None)

    with base.begin() as conn:
        tenants = master_rows.get("tenants") or []
        for t in tenants:
            t["database_name"] = schema
        _upsert_master(conn, Tenant.__table__, tenants, "slug")
        _upsert_master(conn, UserDirectory.__table__, master_rows.get("user_directory") or [], "email")

    now = datetime.now(timezone.utc)
    exported_at = datetime.fromisoformat(meta["exported_at"]) if meta.get("exported_at") else now
    cloud_sync.update_state(slug, cursor=exported_at, last_full_at=now, last_success_at=now, last_error=None, needs_full=False,
                            last_stats={"import": True, "rows": sum(counts.values())})
    from scripts.migrate_db import migrate_schema
    migrate_schema("tenant", schema)
    logger.info(f"Import cloud terminé : {sum(counts.values())} lignes dans {schema}")
    return {"skipped": False, "schema": schema, "counts": counts, "rows": sum(counts.values()), "users": len(master_rows.get("user_directory") or [])}
