"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from auth import require_role, get_current_user
from models.settings import Settings, SettingsUpdate
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/settings", tags=["Settings"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import SettingsRepository
    
    @router.get("/public")
    async def get_public_settings():
        """Get public settings - No authentication required"""
        repo = SettingsRepository()
        settings = repo.get_all()
        return {
            "pharmacy_name": settings.get("pharmacy_name", "DynSoft Pharma"),
            "currency": settings.get("currency", "GNF")
        }
    
    @router.get("/agencies")
    async def get_all_agencies():
        """Get all available agencies - No authentication required"""
        repo = SettingsRepository()
        settings = repo.get_all()
        
        # Récupérer le nom de la pharmacie - utiliser une valeur par défaut si vide
        pharmacy_name = settings.get("pharmacy_name", "").strip()
        if not pharmacy_name:
            pharmacy_name = "DynSoft Pharma"
        
        # Pour PostgreSQL multi-tenant, chaque base = une agence
        return [{
            "tenant_id": "pharmacie_centrale",
            "pharmacy_name": pharmacy_name,
            "currency": settings.get("currency", "GNF")
        }]
    
    @router.get("")
    async def get_settings(current_user: dict = Depends(get_current_user)):
        """Get application settings"""
        repo = SettingsRepository()
        settings = repo.get_all()
        
        # Ajouter les valeurs par défaut
        defaults = {
            "currency": "GNF",
            "stock_valuation_method": "weighted_average",
            "low_stock_threshold": 10,
            "expiration_alert_days": 30,
            "shift_max_duration": 12,
            "pending_sale_expiration_hours": 24,
            "timezone": "Africa/Conakry",
            "debt_overdue_days": 90
        }
        
        for key, default in defaults.items():
            if key not in settings:
                settings[key] = default
        
        return settings
    
    @router.put("")
    async def update_settings(settings_data: SettingsUpdate, current_user: dict = Depends(require_role(["admin"]))):
        """Update application settings (Admin only)"""
        repo = SettingsRepository()
        update_data = {k: v for k, v in settings_data.model_dump().items() if v is not None}
        
        for key, value in update_data.items():
            repo.set(key, value)
        
        return repo.get_all()
