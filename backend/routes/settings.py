from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.settings import Settings, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("/public")
async def get_public_settings():
    """Get public settings (pharmacy name) - No authentication required"""
    # Récupérer les paramètres du tenant par défaut
    settings = await db.settings.find_one({"tenant_id": "default"}, {"_id": 0})
    if settings:
        return {
            "pharmacy_name": settings.get("pharmacy_name", "DynSoft Pharma"),
            "currency": settings.get("currency", "GNF")
        }
    return {
        "pharmacy_name": "DynSoft Pharma",
        "currency": "GNF"
    }

@router.get("/agencies")
async def get_all_agencies():
    """Get all available agencies/pharmacies - No authentication required for login page"""
    # Récupérer toutes les agences depuis la collection settings
    settings_list = await db.settings.find({}, {"_id": 0}).to_list(100)
    
    agencies = []
    for setting in settings_list:
        agencies.append({
            "tenant_id": setting.get("tenant_id", "default"),
            "pharmacy_name": setting.get("pharmacy_name", "Pharmacie"),
            "currency": setting.get("currency", "GNF")
        })
    
    # Si aucune agence, retourner l'agence par défaut
    if not agencies:
        agencies.append({
            "tenant_id": "default",
            "pharmacy_name": "DynSoft Pharma",
            "currency": "GNF"
        })
    
    return agencies

@router.get("")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get application settings"""
    settings = await db.settings.find_one({"tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not settings:
        # Créer les paramètres par défaut
        default_settings = Settings(
            tenant_id=current_user['tenant_id'],
            stock_valuation_method="weighted_average",
            currency="EUR"
        )
        doc = default_settings.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        await db.settings.insert_one(doc)
        settings = doc
    return settings

@router.put("")
async def update_settings(settings_data: SettingsUpdate, current_user: dict = Depends(require_role(["admin"]))):
    """Update application settings (Admin only)"""
    update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.settings.update_one(
        {"tenant_id": current_user['tenant_id']},
        {"$set": update_data},
        upsert=True
    )
    
    settings = await db.settings.find_one({"tenant_id": current_user['tenant_id']}, {"_id": 0})
    return settings
