"""
Routes Plateforme (Super Admin DynSoft) - Gestion des pharmacies (tenants).
"""
import re
import uuid
import unicodedata
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from typing import Optional

from auth import get_current_user, hash_password
from database.config import db_manager
from database.models_master import Tenant, UserDirectory
from database.tenant_context import tenant_schema_name, is_valid_slug, DEFAULT_TENANT
from database.directory import (
    get_directory_entry,
    upsert_directory_entry,
    remove_directory_entries_for_tenant,
)

router = APIRouter(prefix="/platform", tags=["Platform"])

RESERVED_SLUGS = {DEFAULT_TENANT, "default", "public", "platform", "master", "postgres"}


async def require_super_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Accès réservé au Super Admin DynSoft")
    return current_user


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return s[:50]


class PharmacyCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    admin_first_name: str
    admin_last_name: str
    admin_email: str
    admin_password: str


class PharmacyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class AdminPasswordReset(BaseModel):
    email: str
    new_password: str


def _tenant_to_dict(t: Tenant) -> dict:
    return {
        "id": str(t.id),
        "slug": t.slug,
        "name": t.name,
        "address": t.address,
        "phone": t.phone,
        "email": t.email,
        "is_active": t.is_active,
        "schema": t.database_name,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.get("/pharmacies")
async def list_pharmacies(current_user: dict = Depends(require_super_admin)):
    """Liste toutes les pharmacies avec le nombre d'utilisateurs."""
    with db_manager.get_master_session() as session:
        tenants = session.query(Tenant).order_by(Tenant.created_at).all()
        result = [_tenant_to_dict(t) for t in tenants]
        # compter les utilisateurs de l'annuaire par pharmacie
        counts = dict(
            session.query(UserDirectory.tenant_slug, func.count(UserDirectory.id))
            .filter(UserDirectory.tenant_slug.isnot(None))
            .group_by(UserDirectory.tenant_slug)
            .all()
        )
    for r in result:
        r["users_count"] = counts.get(r["slug"], 0)
    return result


@router.post("/pharmacies")
async def create_pharmacy(payload: PharmacyCreate, current_user: dict = Depends(require_super_admin)):
    """Crée une pharmacie : schéma dédié + tables + compte admin + annuaire."""
    slug = (payload.slug or slugify(payload.name)).lower().strip()
    if not is_valid_slug(slug):
        raise HTTPException(status_code=400, detail="Slug invalide (lettres minuscules, chiffres, _ ; 2-50 caractères)")
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=400, detail=f"Le slug '{slug}' est réservé")
    if len(payload.admin_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe admin doit contenir au moins 6 caractères")
    
    admin_email = payload.admin_email.strip().lower()
    
    with db_manager.get_master_session() as session:
        existing = session.query(Tenant).filter(Tenant.slug == slug).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Une pharmacie avec le slug '{slug}' existe déjà")
    
    if get_directory_entry(admin_email):
        raise HTTPException(status_code=400, detail="Cet email admin est déjà utilisé dans le système")
    
    # 1. Créer le schéma + tables
    schema = db_manager.create_tenant_schema(slug)
    
    # 2. Paramètres par défaut de la pharmacie
    from database.repositories import SettingsRepository, UserRepository
    settings_repo = SettingsRepository(slug)
    settings_repo.set("pharmacy_name", payload.name, "Nom de la pharmacie")
    settings_repo.set("currency", "GNF", "Devise")
    settings_repo.set("timezone", "Africa/Conakry", "Fuseau horaire")
    settings_repo.set("low_stock_threshold", 10, "Seuil de stock faible")
    settings_repo.set("expiration_alert_days", 30, "Délai d'alerte de péremption")
    
    # 3. Compte admin de la pharmacie
    user_repo = UserRepository(slug)
    admin_user = user_repo.create({
        "email": admin_email,
        "password": hash_password(payload.admin_password),
        "name": f"{payload.admin_first_name} {payload.admin_last_name}".strip(),
        "employee_code": "ADM-001",
        "role": "admin",
    })
    
    # 4. Enregistrer le tenant + annuaire
    with db_manager.get_master_session() as session:
        tenant = Tenant(
            id=uuid.uuid4(),
            slug=slug,
            name=payload.name,
            address=payload.address,
            phone=payload.phone,
            email=payload.email,
            is_active=True,
            settings={},
            database_name=schema,
        )
        session.add(tenant)
        session.commit()
        tenant_dict = _tenant_to_dict(tenant)
    
    upsert_directory_entry(admin_email, slug)
    
    return {
        "message": f"Pharmacie '{payload.name}' créée avec succès",
        "pharmacy": tenant_dict,
        "admin": {"email": admin_email, "id": admin_user["id"]},
    }


@router.put("/pharmacies/{slug}")
async def update_pharmacy(slug: str, payload: PharmacyUpdate, current_user: dict = Depends(require_super_admin)):
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
        data = payload.model_dump(exclude_none=True)
        for key, value in data.items():
            setattr(tenant, key, value)
        session.commit()
        result = _tenant_to_dict(tenant)
    if "name" in data:
        try:
            from database.repositories import SettingsRepository
            SettingsRepository(slug).set("pharmacy_name", data["name"])
        except Exception:
            pass
    return result


@router.delete("/pharmacies/{slug}")
async def delete_pharmacy(
    slug: str,
    confirm: str = Query(..., description="Retaper le slug pour confirmer"),
    current_user: dict = Depends(require_super_admin),
):
    """Supprime DÉFINITIVEMENT une pharmacie (schéma + données + comptes)."""
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=400, detail="Cette pharmacie ne peut pas être supprimée")
    if confirm != slug:
        raise HTTPException(status_code=400, detail="Confirmation invalide : retapez exactement le slug de la pharmacie")
    
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
        session.delete(tenant)
        session.commit()
    
    db_manager.drop_tenant_schema(slug)
    remove_directory_entries_for_tenant(slug)
    
    return {"message": f"Pharmacie '{slug}' supprimée définitivement"}


@router.post("/pharmacies/{slug}/reset-admin-password")
async def reset_pharmacy_user_password(slug: str, payload: AdminPasswordReset, current_user: dict = Depends(require_super_admin)):
    """Réinitialise le mot de passe d'un utilisateur d'une pharmacie."""
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le mot de passe doit contenir au moins 6 caractères")
    
    from database.repositories import UserRepository
    repo = UserRepository(slug)
    user = repo.get_by_email(payload.email.strip().lower()) or repo.get_by_email(payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé dans cette pharmacie")
    
    repo.update(uuid.UUID(user["id"]), {"password": hash_password(payload.new_password)})
    return {"message": f"Mot de passe de {payload.email} réinitialisé"}
