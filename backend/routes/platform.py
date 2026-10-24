"""
Routes Plateforme (Super Admin DynSoft) - Gestion des pharmacies (tenants).
"""
import re
import uuid
import unicodedata
import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from typing import Optional

from auth import get_current_user, hash_password
from database.config import db_manager
from database.models_master import Tenant, UserDirectory, SyncState
from database.tenant_context import tenant_schema_name, is_valid_slug, DEFAULT_TENANT, FORCED_SCHEMA
from database.directory import (
    get_directory_entry,
    upsert_directory_entry,
    remove_directory_entries_for_tenant,
    invalidate_sync_info,
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
    import_products: bool = False
    source_slug: Optional[str] = None  # pharmacie source du catalogue (défaut: pharmacie centrale)


class PharmacyUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class AdminPasswordReset(BaseModel):
    email: str
    new_password: str


class ChangeOwnPassword(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_own_password(payload: ChangeOwnPassword, current_user: dict = Depends(require_super_admin)):
    """Le super admin change son propre mot de passe (stocké haché en BD)."""
    from auth import verify_password
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 8 caractères")
    
    email = (current_user.get("email") or "").strip().lower()
    entry = get_directory_entry(email)
    if not entry or not entry.get("is_super_admin"):
        raise HTTPException(status_code=404, detail="Compte super admin introuvable")
    if not verify_password(payload.current_password, entry.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Mot de passe actuel incorrect")
    
    upsert_directory_entry(
        email, tenant_slug=None, is_super_admin=True,
        password_hash=hash_password(payload.new_password), name=entry.get("name"),
    )
    return {"message": "Mot de passe modifié avec succès"}


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
def list_pharmacies(current_user: dict = Depends(require_super_admin)):
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
        sync_states = {st.slug: st for st in session.query(SyncState).all()}
        for r in result:
            st = sync_states.get(r["slug"])
            r["sync"] = {
                "mode": (next((t for t in tenants if t.slug == r["slug"]), None).settings or {}).get("sync_mode"),
                "last_success_at": st.last_success_at.isoformat() if st and st.last_success_at else None,
                "last_error": st.last_error if st else None,
                "rows": (st.last_stats or {}).get("rows") if st else None,
            }
    for r in result:
        r["users_count"] = counts.get(r["slug"], 0)
    return result


@router.post("/pharmacies/{slug}/sync-token")
def create_sync_token(slug: str, current_user: dict = Depends(require_super_admin)):
    """Génère (ou régénère) le jeton de synchronisation du serveur local de la pharmacie.
    Le jeton n'est affiché qu'une fois ; la copie cloud passe en consultation seule."""
    token = secrets.token_urlsafe(36)
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie introuvable")
        settings = dict(tenant.settings or {})
        settings.update({
            "sync_mode": "mirror",
            "sync_token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "sync_token_created_at": datetime.now(timezone.utc).isoformat(),
        })
        tenant.settings = settings
        session.commit()
    invalidate_sync_info(slug)
    return {"slug": slug, "token": token, "cloud_url_hint": "URL publique de DynSoft Pharma (ex. https://votre-domaine)"}


@router.delete("/pharmacies/{slug}/sync-token")
def revoke_sync_token(slug: str, current_user: dict = Depends(require_super_admin)):
    """Désactive la synchronisation : la copie cloud redevient modifiable."""
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie introuvable")
        settings = {k: v for k, v in (tenant.settings or {}).items() if not k.startswith("sync_")}
        tenant.settings = settings
        session.commit()
    invalidate_sync_info(slug)
    return {"slug": slug, "sync_mode": None}


@router.get("/pharmacies/stats")
def pharmacies_stats(current_user: dict = Depends(require_super_admin)):
    """Chiffre d'affaires par pharmacie (jour, mois en cours, total) pour le super admin."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from database.models_tenant import Sale, SaleStatus
    from database.repositories import SettingsRepository
    from services.tz_service import local_day_bounds, now_local, DEFAULT_TIMEZONE

    with db_manager.get_master_session() as session:
        tenants = [(t.slug, t.is_active) for t in session.query(Tenant).order_by(Tenant.created_at).all()]

    stats = {}
    for slug, is_active in tenants:
        entry = {"ca_today": 0, "ca_month": 0, "ca_total": 0, "sales_today": 0, "sales_month": 0, "sales_total": 0, "error": None}
        try:
            try:
                tz = ZoneInfo(SettingsRepository(slug).get("timezone", DEFAULT_TIMEZONE))
            except Exception:
                tz = ZoneInfo(DEFAULT_TIMEZONE)
            today_local = now_local(tz).date()
            day_start, day_end = local_day_bounds(today_local, tz)
            month_start, _ = local_day_bounds(today_local.replace(day=1), tz)

            with db_manager.get_tenant_session(slug) as s:
                base = s.query(func.coalesce(func.sum(Sale.total), 0), func.count(Sale.id)).filter(
                    Sale.status != SaleStatus.CANCELLED
                )
                ca_total, n_total = base.first()
                ca_month, n_month = base.filter(Sale.created_at >= month_start).first()
                ca_today, n_today = base.filter(Sale.created_at >= day_start, Sale.created_at < day_end).first()

            entry.update({
                "ca_today": float(ca_today or 0), "sales_today": int(n_today or 0),
                "ca_month": float(ca_month or 0), "sales_month": int(n_month or 0),
                "ca_total": float(ca_total or 0), "sales_total": int(n_total or 0),
            })
        except Exception:
            entry["error"] = "Données indisponibles"
        stats[slug] = entry

    return {"stats": stats, "month": now_local().strftime("%Y-%m")}


def _copy_catalog(source_slug: str, target_slug: str) -> dict:
    """Copie le catalogue (catégories, unités, produits) + règles de rabais et codes promo
    (désactivés) d'une pharmacie vers une autre. Stock remis à zéro."""
    from database.models_tenant import Product, Category, Unit, DiscountRule, PromoCode, PromoCodeStatus
    
    with db_manager.get_tenant_session(source_slug) as src:
        categories = [
            {"name": c.name, "description": c.description, "color": c.color,
             "markup_coefficient": c.markup_coefficient, "min_stock": c.min_stock, "old_id": c.id}
            for c in src.query(Category).all()
        ]
        units = [
            {"name": u.name, "abbreviation": u.abbreviation, "description": u.description, "old_id": u.id}
            for u in src.query(Unit).all()
        ]
        products = [
            {"name": p.name, "internal_reference": p.internal_reference, "barcode": p.barcode,
             "description": p.description, "purchase_price": p.purchase_price, "price": p.price,
             "min_stock": p.min_stock, "is_active": p.is_active,
             "category_id": p.category_id, "unit_id": p.unit_id}
            for p in src.query(Product).filter(Product.is_active == True).all()
        ]
        discount_rules = [
            {"name": r.name, "description": r.description, "rule_type": r.rule_type,
             "discount_type": r.discount_type, "discount_value": r.discount_value,
             "max_discount_amount": r.max_discount_amount, "conditions": r.conditions,
             "priority": r.priority, "is_cumulative": r.is_cumulative,
             "start_date": r.start_date, "end_date": r.end_date}
            for r in src.query(DiscountRule).all()
        ]
        promo_codes = [
            {"code": pc.code, "name": pc.name, "description": pc.description,
             "discount_type": pc.discount_type, "discount_value": pc.discount_value,
             "min_purchase_amount": pc.min_purchase_amount, "max_discount_amount": pc.max_discount_amount,
             "start_date": pc.start_date, "end_date": pc.end_date,
             "max_uses": pc.max_uses, "max_uses_per_customer": pc.max_uses_per_customer,
             "first_purchase_only": pc.first_purchase_only}
            for pc in src.query(PromoCode).all()
        ]
    
    cat_map, unit_map = {}, {}
    with db_manager.get_tenant_session(target_slug) as dst:
        for c in categories:
            new_id = uuid.uuid4()
            cat_map[c.pop("old_id")] = new_id
            dst.add(Category(id=new_id, **c))
        for u in units:
            new_id = uuid.uuid4()
            unit_map[u.pop("old_id")] = new_id
            dst.add(Unit(id=new_id, **u))
        dst.flush()
        for p in products:
            dst.add(Product(
                id=uuid.uuid4(),
                stock=0,
                category_id=cat_map.get(p.pop("category_id")),
                unit_id=unit_map.get(p.pop("unit_id")),
                **p,
            ))
        for r in discount_rules:
            conditions = r.pop("conditions")
            if isinstance(conditions, dict) and isinstance(conditions.get("category_ids"), list):
                str_cat_map = {str(k): v for k, v in cat_map.items()}
                conditions = {**conditions, "category_ids": [
                    str(str_cat_map[str(old)]) for old in conditions["category_ids"] if str(old) in str_cat_map
                ]}
            dst.add(DiscountRule(id=uuid.uuid4(), is_active=False, conditions=conditions, created_by=None, **r))
        for pc in promo_codes:
            dst.add(PromoCode(
                id=uuid.uuid4(), status=PromoCodeStatus.INACTIVE, current_uses=0,
                applicable_categories=None, applicable_products=None, customer_types=None,
                created_by=None, **pc,
            ))
        dst.commit()
    
    return {
        "categories": len(categories), "units": len(units), "products": len(products),
        "discount_rules": len(discount_rules), "promo_codes": len(promo_codes),
    }


@router.post("/pharmacies")
def create_pharmacy(payload: PharmacyCreate, current_user: dict = Depends(require_super_admin)):
    """Crée une pharmacie : schéma dédié + tables + compte admin + annuaire."""
    if FORCED_SCHEMA:
        raise HTTPException(status_code=400, detail=f"Ce serveur est dédié à une seule pharmacie (TENANT_SCHEMA={FORCED_SCHEMA}) : création impossible")
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
    
    # 5. Import optionnel du catalogue produits (stock à zéro)
    imported = None
    if payload.import_products:
        source = payload.source_slug or DEFAULT_TENANT
        with db_manager.get_master_session() as session:
            if source != DEFAULT_TENANT and not session.query(Tenant).filter(Tenant.slug == source).first():
                raise HTTPException(status_code=400, detail=f"Pharmacie source '{source}' introuvable")
        imported = _copy_catalog(source, slug)
    
    message = f"Pharmacie '{payload.name}' créée avec succès"
    if imported:
        message += (f" — catalogue importé : {imported['products']} produits, {imported['categories']} catégories, "
                    f"{imported['discount_rules']} règles et {imported['promo_codes']} codes promo (désactivés)")
    
    return {
        "message": message,
        "pharmacy": tenant_dict,
        "admin": {"email": admin_email, "id": admin_user["id"]},
        "imported": imported,
    }


@router.put("/pharmacies/{slug}")
def update_pharmacy(slug: str, payload: PharmacyUpdate, current_user: dict = Depends(require_super_admin)):
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
def delete_pharmacy(
    slug: str,
    confirm: str = Query(..., description="Retaper le slug pour confirmer"),
    current_user: dict = Depends(require_super_admin),
):
    """Supprime DÉFINITIVEMENT une pharmacie (schéma + données + comptes)."""
    if FORCED_SCHEMA:
        raise HTTPException(status_code=400, detail=f"Ce serveur est dédié à une seule pharmacie (TENANT_SCHEMA={FORCED_SCHEMA}) : suppression impossible")
    if slug in RESERVED_SLUGS:
        raise HTTPException(status_code=400, detail="Cette pharmacie ne peut pas être supprimée")
    if confirm != slug:
        raise HTTPException(status_code=400, detail="Confirmation invalide : retapez exactement le slug de la pharmacie")
    
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
    
    # Supprimer le schéma d'abord : en cas d'échec, l'enregistrement reste et on peut réessayer
    db_manager.drop_tenant_schema(slug)
    remove_directory_entries_for_tenant(slug)
    
    with db_manager.get_master_session() as session:
        session.query(Tenant).filter(Tenant.slug == slug).delete(synchronize_session=False)
        session.commit()
    
    return {"message": f"Pharmacie '{slug}' supprimée définitivement"}


@router.post("/pharmacies/{slug}/reset-admin-password")
def reset_pharmacy_user_password(slug: str, payload: AdminPasswordReset, current_user: dict = Depends(require_super_admin)):
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



def _tenant_or_404(slug: str) -> Tenant:
    with db_manager.get_master_session() as session:
        tenant = session.query(Tenant).filter(Tenant.slug == slug).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Pharmacie non trouvée")
        session.expunge(tenant)
        return tenant


@router.post("/pharmacies/{slug}/reset-data")
def reset_pharmacy_data(
    slug: str,
    confirm: str = Query(..., description="Retaper le slug pour confirmer"),
    backup: bool = Query(True),
    current_user: dict = Depends(require_super_admin),
):
    """Remet une pharmacie à zéro (ventes, appros, stock, dettes...) en conservant utilisateurs, produits,
    fournisseurs, clients, paramètres et codes promo. Sauvegarde automatique en base avant purge."""
    from services.tenant_reset import reset_tenant_data
    if confirm != slug:
        raise HTTPException(status_code=400, detail="Confirmation invalide : retapez exactement le slug de la pharmacie")
    _tenant_or_404(slug)
    try:
        result = reset_tenant_data(tenant_schema_name(slug), backup=backup)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Réinitialisation échouée (aucune donnée modifiée) : {exc}")
    invalidate_sync_info(slug)
    result["message"] = f"Pharmacie '{slug}' réinitialisée"
    result["by"] = current_user.get("email")
    result["at"] = datetime.now(timezone.utc).isoformat()
    return result


@router.get("/pharmacies/{slug}/backups")
def list_pharmacy_backups(slug: str, current_user: dict = Depends(require_super_admin)):
    from services.tenant_reset import list_backups
    _tenant_or_404(slug)
    return list_backups(tenant_schema_name(slug))


@router.delete("/pharmacies/{slug}/backups/{name}")
def delete_pharmacy_backup(slug: str, name: str, current_user: dict = Depends(require_super_admin)):
    from services.tenant_reset import drop_backup, BACKUP_PREFIX
    _tenant_or_404(slug)
    if not name.startswith(f"{BACKUP_PREFIX}{tenant_schema_name(slug)}_"):
        raise HTTPException(status_code=400, detail="Cette sauvegarde n'appartient pas à cette pharmacie")
    try:
        drop_backup(name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"message": f"Sauvegarde {name} supprimée"}
