"""Recherche publique (sans connexion) des pharmacies ayant un produit en stock."""
import os
import re
import time
import logging
import unicodedata
from collections import defaultdict, deque
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import or_

from database.config import db_manager
from database.models_master import Tenant
from database.models_tenant import Product
from database.tenant_context import tenant_schema_name, FORCED_SCHEMA
from database.repositories import SettingsRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Public"])

CLOUD_SYNC_URL = os.environ.get("CLOUD_SYNC_URL", "").rstrip("/")
MAX_PRODUCTS_PER_PHARMACY = 5
RATE_LIMIT = 30  # requêtes / minute / IP
_hits: dict = defaultdict(deque)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return re.sub(r"\s+", " ", "".join(c for c in text if not unicodedata.combining(c)).lower()).strip()


def _rate_limit(request: Request):
    ip = request.client.host if request.client else "?"
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Trop de recherches, réessayez dans une minute.")
    q.append(now)


def _location_matches(location: str, *addresses: str) -> bool:
    words = [w for w in _norm(location).split(" ") if len(w) >= 2]
    if not words:
        return True
    haystack = " ".join(_norm(a) for a in addresses if a)
    return all(w in haystack for w in words)


def _search_tenant(tenant: Tenant, product: str, location: Optional[str]):
    info = {}
    try:
        info = SettingsRepository(tenant.slug).get_all()
    except Exception:
        pass
    address = tenant.address or info.get("pharmacy_address") or ""
    phone = tenant.phone or info.get("pharmacy_phone") or ""
    if location and not _location_matches(location, tenant.address, info.get("pharmacy_address")):
        return None

    words = [w for w in product.strip().split() if w]
    with db_manager.get_tenant_session(tenant.slug) as session:
        q = session.query(Product.name).filter(Product.is_active == True, Product.stock > 0)
        for w in words:
            q = q.filter(or_(Product.name.ilike(f"%{w}%"), Product.barcode == w, Product.internal_reference.ilike(f"%{w}%")))
        total = q.count()
        if total == 0:
            return None
        names = [r[0] for r in q.order_by(Product.name).limit(MAX_PRODUCTS_PER_PHARMACY).all()]
    return {
        "name": tenant.name or info.get("pharmacy_name") or tenant.slug,
        "address": address,
        "phone": phone,
        "products": names,
        "total_matches": total,
    }


def _local_tenants():
    with db_manager.get_master_session() as session:
        tenants = session.query(Tenant).filter(Tenant.is_active == True).order_by(Tenant.name).all()
        result = []
        for t in tenants:
            if not (t.settings or {}).get("public_search_enabled", True):
                continue
            if FORCED_SCHEMA and tenant_schema_name(t.slug) != FORCED_SCHEMA:
                continue
            session.expunge(t)
            result.append(t)
        return result


@router.get("/pharmacies/search")
def search_pharmacies(
    request: Request,
    product: str = Query(..., min_length=3, max_length=100, description="Nom, référence ou code-barres du produit"),
    location: Optional[str] = Query(None, max_length=100, description="Ville, commune ou quartier"),
):
    """Liste les pharmacies (actives et autorisées) ayant le produit en stock."""
    _rate_limit(request)
    product = product.strip()
    location = (location or "").strip() or None

    # Installation locale : la liste complète des pharmacies est sur le cloud
    if FORCED_SCHEMA and CLOUD_SYNC_URL:
        try:
            r = requests.get(f"{CLOUD_SYNC_URL}/api/public/pharmacies/search",
                             params={"product": product, "location": location or ""}, timeout=8)
            if r.ok:
                return r.json()
        except Exception as exc:
            logger.warning(f"Recherche publique cloud indisponible : {exc}")

    pharmacies = []
    for tenant in _local_tenants():
        try:
            hit = _search_tenant(tenant, product, location)
        except Exception as exc:
            logger.warning(f"Recherche publique {tenant.slug} : {exc}")
            hit = None
        if hit:
            pharmacies.append(hit)

    return {"product": product, "location": location, "count": len(pharmacies), "pharmacies": pharmacies}
