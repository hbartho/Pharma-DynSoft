"""Synchronisation cloud : réception (côté DynSoft cloud) et pilotage local (côté pharmacie)."""
import hashlib
import logging
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth import require_admin
from database.config import db_manager
from database.models_master import Tenant
from database.tenant_context import tenant_schema_name
from services import cloud_sync

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cloud-sync", tags=["Cloud Sync"])


class BeginPayload(BaseModel):
    full: bool = False


class PushPayload(BaseModel):
    session_id: str
    table: str
    rows: List[Dict[str, Any]]


class FinishPayload(BaseModel):
    session_id: str
    cursor: Optional[str] = None
    stats: Dict[str, Any] = {}


# ---------- côté local (pharmacie) ----------
@router.get("/local/status")
def local_status(current_user: dict = Depends(require_admin)):
    if not cloud_sync.LOCAL_ENABLED:
        return {"enabled": False}
    state = cloud_sync.get_state(cloud_sync.CLOUD_SYNC_SLUG)
    return {
        "enabled": True,
        "cloud_url": cloud_sync.CLOUD_SYNC_URL,
        "slug": cloud_sync.CLOUD_SYNC_SLUG,
        "sync_hour": cloud_sync.CLOUD_SYNC_HOUR,
        "running": cloud_sync._lock.locked(),
        **{k: state.get(k) for k in ("last_success_at", "last_attempt_at", "last_full_at", "last_error", "last_stats", "needs_full")},
    }


@router.post("/local/run")
def local_run(full: bool = False, current_user: dict = Depends(require_admin)):
    if not cloud_sync.LOCAL_ENABLED:
        raise HTTPException(status_code=400, detail="Synchronisation cloud non configurée sur ce serveur")
    if cloud_sync._lock.locked():
        return {"started": False, "message": "Une synchronisation est déjà en cours"}
    if full:
        cloud_sync.update_state(cloud_sync.CLOUD_SYNC_SLUG, needs_full=True)
    cloud_sync.trigger_sync()
    return {"started": True}


# ---------- côté cloud (récepteur, authentifié par jeton) ----------
def verify_sync_token(slug: str, x_sync_token: str = Header(default="")) -> Tenant:
    if not x_sync_token:
        raise HTTPException(status_code=401, detail="Jeton de synchronisation manquant")
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant or not tenant.is_active:
            raise HTTPException(status_code=404, detail="Pharmacie inconnue ou désactivée")
        settings = tenant.settings or {}
        expected = settings.get("sync_token_hash")
        if settings.get("sync_mode") != "mirror" or not expected:
            raise HTTPException(status_code=403, detail="Synchronisation non activée pour cette pharmacie")
        if hashlib.sha256(x_sync_token.encode()).hexdigest() != expected:
            raise HTTPException(status_code=401, detail="Jeton de synchronisation invalide")
        session.expunge(tenant)
        return tenant


@router.get("/{slug}/state")
def cloud_state(slug: str, tenant: Tenant = Depends(verify_sync_token)):
    return cloud_sync.get_state(slug)


@router.get("/{slug}/export")
def cloud_export(slug: str, tenant: Tenant = Depends(verify_sync_token)):
    """Export complet (NDJSON) de la pharmacie pour initialiser un serveur local."""
    return StreamingResponse(cloud_sync.iter_export(slug, tenant_schema_name(slug)), media_type="application/x-ndjson")


@router.post("/{slug}/begin")
def cloud_begin(slug: str, payload: BeginPayload, tenant: Tenant = Depends(verify_sync_token)):
    return cloud_sync.cloud_begin(slug, tenant_schema_name(slug), payload.full)


@router.post("/{slug}/push")
def cloud_push(slug: str, payload: PushPayload, tenant: Tenant = Depends(verify_sync_token)):
    try:
        n = cloud_sync.cloud_push(slug, tenant_schema_name(slug), payload.session_id, payload.table, payload.rows)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"table": payload.table, "upserted": n}


@router.post("/{slug}/finish")
def cloud_finish(slug: str, payload: FinishPayload, tenant: Tenant = Depends(verify_sync_token)):
    try:
        return cloud_sync.cloud_finish(slug, tenant_schema_name(slug), payload.session_id, payload.cursor, payload.stats)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
