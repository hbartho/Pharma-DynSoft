"""Contexte tenant (pharmacie courante) basé sur contextvars.
Le slug est positionné à chaque requête par get_current_user (JWT).
"""
import re
from contextvars import ContextVar

DEFAULT_TENANT = "pharmacie_centrale"

_current_tenant: ContextVar[str] = ContextVar("current_tenant", default=DEFAULT_TENANT)


def set_current_tenant(slug: str):
    _current_tenant.set(slug or DEFAULT_TENANT)


def get_current_tenant() -> str:
    return _current_tenant.get()


def tenant_schema_name(tenant_slug: str = None) -> str:
    """Nom du schéma PostgreSQL pour une pharmacie.
    La pharmacie historique (pharmacie_centrale) reste dans le schéma public."""
    slug = tenant_slug or get_current_tenant()
    if slug in (DEFAULT_TENANT, "default", None, ""):
        return "public"
    clean = re.sub(r"[^a-z0-9_]", "_", slug.lower().strip())
    if not clean:
        clean = "invalid"
    return f"t_{clean}"


def is_valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9_]{2,50}", slug or ""))
