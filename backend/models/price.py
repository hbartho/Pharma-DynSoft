from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid

class PriceChangeType(str, Enum):
    INITIAL = "initial"              # Prix initial
    MANUAL = "manual"                # Modification manuelle
    SUPPLY = "supply"                # Mise à jour via approvisionnement
    CATEGORY = "category"            # Calcul via coefficient catégorie
    PROMOTION = "promotion"          # Prix promotionnel
    ADJUSTMENT = "adjustment"        # Ajustement

class PriceHistory(BaseModel):
    """Historique des prix d'un produit"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: Optional[str] = None  # Dénormalisé pour affichage
    purchase_price: float  # Prix d'achat
    selling_price: float   # Prix de vente
    purchase_price_before: Optional[float] = None  # Prix achat avant
    selling_price_before: Optional[float] = None   # Prix vente avant
    change_type: PriceChangeType
    reference_type: Optional[str] = None  # supply, manual, category
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    effective_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None

class PriceHistoryCreate(BaseModel):
    product_id: str
    purchase_price: float
    selling_price: float
    change_type: PriceChangeType
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None
    effective_date: Optional[datetime] = None

class PriceSummary(BaseModel):
    """Résumé des prix d'un produit"""
    product_id: str
    product_name: str
    current_purchase_price: float
    current_selling_price: float
    price_changes_count: int
    last_change_date: Optional[datetime] = None
