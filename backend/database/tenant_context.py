"""Contexte tenant (pharmacie courante) basé sur contextvars.
Le slug est positionné à chaque requête par get_current_user (JWT).
"""
import os
import re
from contextvars import ContextVar

DEFAULT_TENANT = "pharmacie_centrale"

# Serveur local dédié à UNE pharmacie : toutes les requêtes utilisent ce schéma (ex. t_noormin ou public)
FORCED_SCHEMA = re.sub(r"[^a-z0-9_]", "", os.environ.get("TENANT_SCHEMA", "").strip().lower())

_current_tenant: ContextVar[str] = ContextVar("current_tenant", default=DEFAULT_TENANT)


def set_current_tenant(slug: str):
    _current_tenant.set(slug or DEFAULT_TENANT)


def get_current_tenant() -> str:
    return _current_tenant.get()


def tenant_schema_name(tenant_slug: str = None) -> str:
    """Nom du schéma PostgreSQL pour une pharmacie.
    La pharmacie historique (pharmacie_centrale) reste dans le schéma public."""
    if FORCED_SCHEMA:
        return FORCED_SCHEMA
    slug = tenant_slug or get_current_tenant()
    if slug in (DEFAULT_TENANT, "default", None, ""):
        return "public"
    clean = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())
    if not clean:
        clean = "invalid"
    return f"t_{clean}"


def is_valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]{2,50}", slug or ""))
