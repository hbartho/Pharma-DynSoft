"""Synchronisation cloud : remontée du schéma d'une pharmacie (local → DynSoft cloud).
Côté local (émetteur) : CloudSyncClient + scheduler nocturne. Côté cloud (récepteur) : fonctions apply_*.
Le schéma public n'est jamais synchronisé.
"""
import os
import uuid
import enum
import logging
import threading
import time
from decimal import Decimal
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, List, Optional

import requests
from sqlalchemy import select, text, Table, DateTime, Date, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, insert as pg_insert

from database.base import Base
import database.models_tenant  # noqa: F401
from database.config import db_manager
from database.models_master import SyncState

logger = logging.getLogger(__name__)

CLOUD_SYNC_URL = os.environ.get("CLOUD_SYNC_URL", "").rstrip("/")
CLOUD_SYNC_TOKEN = os.environ.get("CLOUD_SYNC_TOKEN", "")
CLOUD_SYNC_SLUG = os.environ.get("CLOUD_SYNC_SLUG", "").strip().lower()
CLOUD_SYNC_HOUR = int(os.environ.get("CLOUD_SYNC_HOUR", "2"))
FULL_EVERY_DAYS = 7
CHUNK = 300
CURSOR_OVERLAP = timedelta(minutes=5)
LOCAL_ENABLED = bool(CLOUD_SYNC_URL and CLOUD_SYNC_TOKEN and CLOUD_SYNC_SLUG)


def tenant_tables() -> List[Table]:
    return [t for t in Base.metadata.sorted_tables if t.schema is None]


def table_by_name(name: str) -> Optional[Table]:
    return next((t for t in tenant_tables() if t.name == name), None)


def parent_link(table: Table):
    """Pour une table sans updated_at : (table parente avec updated_at, colonne FK locale)."""
    for fk in table.foreign_keys:
        parent = fk.column.table
        if "updated_at" in parent.c:
            return parent, fk.parent
    return None, None


# ---------- (dé)sérialisation ----------
def serialize_value(v):
    if isinstance(v, enum.Enum):
        return v.name
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def serialize_row(row) -> Dict[str, Any]:
    return {k: serialize_value(v) for k, v in dict(row._mapping).items()}


def deserialize_row(table: Table, row: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for col in table.columns:
        if col.name not in row:
            continue
        v = row[col.name]
        if v is not None:
            t = col.type
            if isinstance(t, PGUUID):
                v = uuid.UUID(v)
            elif isinstance(t, DateTime):
                v = datetime.fromisoformat(v)
            elif isinstance(t, Date):
                v = date.fromisoformat(v)
            elif isinstance(t, SAEnum) and t.enum_class is not None:
                v = t.enum_class[v] if v in t.enum_class.__members__ else t.enum_class(v)
        out[col.name] = v
    return out


# ---------- état (public.sync_state) ----------
def get_state(slug: str) -> Dict[str, Any]:
    with db_manager.get_master_session() as session:
        st = session.query(SyncState).filter(SyncState.slug == slug).first()
        if not st:
            return {"slug": slug}
        return {
            "slug": slug,
            "cursor": st.cursor.isoformat() if st.cursor else None,
            "last_full_at": st.last_full_at.isoformat() if st.last_full_at else None,
            "last_success_at": st.last_success_at.isoformat() if st.last_success_at else None,
            "last_attempt_at": st.last_attempt_at.isoformat() if st.last_attempt_at else None,
            "last_error": st.last_error,
            "last_stats": st.last_stats or {},
            "needs_full": bool(st.needs_full),
            "active_session_id": st.active_session_id,
            "active_full": bool(st.active_full),
        }


def update_state(slug: str, **fields):
    with db_manager.get_master_session() as session:
        st = session.query(SyncState).filter(SyncState.slug == slug).first()
        if not st:
            st = SyncState(id=uuid.uuid4(), slug=slug, last_stats={})
            session.add(st)
        for k, v in fields.items():
            setattr(st, k, v)
        session.commit()


# ======================================================================
# CÔTÉ CLOUD (récepteur)
# ======================================================================
def staging_schema(schema: str) -> str:
    return f"{schema}__staging"


def cloud_begin(slug: str, schema: str, full: bool) -> Dict[str, Any]:
    session_id = uuid.uuid4().hex
    target = staging_schema(schema) if full else schema
    engine = db_manager.schema_engine("public")
    if full:
        with engine.connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{target}" CASCADE'))
            conn.commit()
    db_manager.create_schema_tables(target)
    update_state(slug, active_session_id=session_id, active_full=full, last_attempt_at=datetime.now(timezone.utc))
    return {"session_id": session_id, "full": full, "schema": target}


def cloud_push(slug: str, schema: str, session_id: str, table_name: str, rows: List[Dict[str, Any]]) -> int:
    state = get_state(slug)
    if state.get("active_session_id") != session_id:
        raise ValueError("Session de synchronisation invalide ou expirée")
    table = table_by_name(table_name)
    if table is None:
        raise ValueError(f"Table inconnue: {table_name}")
    target = staging_schema(schema) if state.get("active_full") else schema
    engine = db_manager.schema_engine(target)
    values = [deserialize_row(table, r) for r in rows]
    if not values:
        return 0
    with engine.begin() as conn:
        for i in range(0, len(values), 200):
            stmt = pg_insert(table).values(values[i:i + 200])
            stmt = stmt.on_conflict_do_update(
                index_elements=[table.c.id],
                set_={c.name: stmt.excluded[c.name] for c in table.columns if c.name != "id"},
            )
            conn.execute(stmt)
    return len(values)


def cloud_finish(slug: str, schema: str, session_id: str, cursor: Optional[str], stats: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state(slug)
    if state.get("active_session_id") != session_id:
        raise ValueError("Session de synchronisation invalide ou expirée")
    now = datetime.now(timezone.utc)
    if state.get("active_full"):
        stg = staging_schema(schema)
        with db_manager.schema_engine("public").connect() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            conn.execute(text(f'ALTER SCHEMA "{stg}" RENAME TO "{schema}"'))
            conn.commit()
        db_manager._schema_session_factories.pop(schema, None)
    update_state(
        slug,
        active_session_id=None, active_full=False,
        last_success_at=now, last_error=None, last_stats=stats or {},
        cursor=datetime.fromisoformat(cursor) if cursor else None,
        **({"last_full_at": now} if state.get("active_full") else {}),
    )
    return get_state(slug)


# ======================================================================
# CÔTÉ LOCAL (émetteur)
# ======================================================================
class CloudSyncClient:
    def __init__(self, schema: str):
        self.schema = schema
        self.base = f"{CLOUD_SYNC_URL}/api/cloud-sync/{CLOUD_SYNC_SLUG}"
        self.headers = {"X-Sync-Token": CLOUD_SYNC_TOKEN}
        self.engine = db_manager.schema_engine(schema)

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base}/{path}", json=payload, headers=self.headers, timeout=120)
        if r.status_code >= 400:
            raise RuntimeError(f"Cloud {r.status_code} sur {path}: {r.text[:200]}")
        return r.json()

    def ping(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/state", headers=self.headers, timeout=20)
        if r.status_code >= 400:
            raise RuntimeError(f"Cloud {r.status_code}: {r.text[:200]}")
        return r.json()

    def _iter_rows(self, table: Table, since: Optional[datetime]):
        with self.engine.connect() as conn:
            if since is None:
                stmt = select(table)
            elif "updated_at" in table.c:
                stmt = select(table).where(table.c.updated_at > since)
            else:
                parent, fk_col = parent_link(table)
                if parent is None:
                    stmt = select(table)
                else:
                    stmt = select(table).join(parent, fk_col == parent.c.id).where(parent.c.updated_at > since)
            result = conn.execution_options(stream_results=True).execute(stmt)
            while True:
                chunk = result.fetchmany(CHUNK)
                if not chunk:
                    break
                yield [serialize_row(r) for r in chunk]

    def run(self, force_full: bool = False) -> Dict[str, Any]:
        state = get_state(CLOUD_SYNC_SLUG)
        now = datetime.now(timezone.utc)
        last_full = datetime.fromisoformat(state["last_full_at"]) if state.get("last_full_at") else None
        full = force_full or state.get("needs_full") or last_full is None or (now - last_full) > timedelta(days=FULL_EVERY_DAYS)
        since = None if full else (datetime.fromisoformat(state["cursor"]) - CURSOR_OVERLAP if state.get("cursor") else None)
        if since is None:
            full = True
        new_cursor = now
        update_state(CLOUD_SYNC_SLUG, last_attempt_at=now)
        try:
            begin = self._post("begin", {"full": full})
            session_id = begin["session_id"]
            stats = {"full": full, "tables": {}}
            for table in tenant_tables():
                sent = 0
                for rows in self._iter_rows(table, since):
                    self._post("push", {"session_id": session_id, "table": table.name, "rows": rows})
                    sent += len(rows)
                if sent:
                    stats["tables"][table.name] = sent
            stats["rows"] = sum(stats["tables"].values())
            self._post("finish", {"session_id": session_id, "cursor": new_cursor.isoformat(), "stats": stats})
            update_state(
                CLOUD_SYNC_SLUG, cursor=new_cursor, last_success_at=datetime.now(timezone.utc),
                last_error=None, last_stats=stats, needs_full=False,
                **({"last_full_at": now} if full else {}),
            )
            logger.info(f"Synchro cloud OK ({'complète' if full else 'incrémentale'}) : {stats['rows']} lignes")
            return {"ok": True, **stats}
        except Exception as e:
            msg = str(e)[:500]
            logger.warning(f"Synchro cloud échouée : {msg}")
            update_state(CLOUD_SYNC_SLUG, last_error=msg, **({"needs_full": True} if "IntegrityError" in msg or "violates" in msg else {}))
            return {"ok": False, "error": msg}


# ---------- scheduler nocturne (thread) ----------
_lock = threading.Lock()
_run_now = threading.Event()
_last_fail_at: Optional[datetime] = None
RETRY_AFTER = timedelta(minutes=15)


def run_sync(force_full: bool = False) -> Dict[str, Any]:
    from database.tenant_context import tenant_schema_name
    if not LOCAL_ENABLED:
        return {"ok": False, "error": "Synchronisation cloud non configurée (CLOUD_SYNC_URL / CLOUD_SYNC_TOKEN / CLOUD_SYNC_SLUG)"}
    if not _lock.acquire(blocking=False):
        return {"ok": False, "error": "Une synchronisation est déjà en cours"}
    try:
        return CloudSyncClient(tenant_schema_name(CLOUD_SYNC_SLUG)).run(force_full=force_full)
    finally:
        _lock.release()


def trigger_sync():
    _run_now.set()


def _due(state: Dict[str, Any]) -> bool:
    global _last_fail_at
    now = datetime.now()  # heure locale du serveur (TZ du conteneur)
    last_ok = state.get("last_success_at")
    synced_today = bool(last_ok) and datetime.fromisoformat(last_ok).astimezone().date() == now.date()
    if synced_today or now.hour < CLOUD_SYNC_HOUR:
        return False
    if _last_fail_at and datetime.now(timezone.utc) - _last_fail_at < RETRY_AFTER:
        return False  # Internet absent : nouvelle tentative dans 15 min
    return True


def _loop():
    global _last_fail_at
    time.sleep(20)
    while True:
        try:
            forced = _run_now.wait(timeout=60)
            _run_now.clear()
            if forced or _due(get_state(CLOUD_SYNC_SLUG)):
                result = run_sync()
                _last_fail_at = None if result.get("ok") else datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Scheduler synchro : {e}")
            _last_fail_at = datetime.now(timezone.utc)


def start_scheduler():
    if not LOCAL_ENABLED:
        return
    threading.Thread(target=_loop, name="cloud-sync", daemon=True).start()
    logger.info(f"Synchro cloud activée : {CLOUD_SYNC_SLUG} → {CLOUD_SYNC_URL} (chaque nuit à {CLOUD_SYNC_HOUR}h)")
