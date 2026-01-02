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
    """Historique des prix d'un produit - Table PRIX"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Référence produit
    product_id: str                              # ref_prod (ID)
    product_name: Optional[str] = None           # Nom du produit (dénormalisé)
    product_reference: Optional[str] = None      # ref_prod (référence interne)
    
    # Prix
    purchase_price: float                        # prix_appro - Prix d'achat
    selling_price: float                         # prix_vente_prod - Prix de vente
    purchase_price_before: Optional[float] = None  # Prix achat avant modification
    selling_price_before: Optional[float] = None   # Prix vente avant modification
    
    # Dates
    price_update_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # date_maj_prix
    supply_date: Optional[datetime] = None       # date_appro - Date de l'approvisionnement
    expiration_date: Optional[datetime] = None   # date_peremption
    
    # Type et référence
    change_type: PriceChangeType
    reference_type: Optional[str] = None         # supply, manual, category
    reference_id: Optional[str] = None           # ID de la référence
    notes: Optional[str] = None
    
    # Agence
    tenant_id: str                               # IDAgence
    
    # Traçabilité - Utiliser employee_code
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # modifier_le
    created_by: Optional[str] = None             # ID utilisateur
    created_by_code: Optional[str] = None        # modifier_par - Code employé (ex: ADM-001)
    
    modified_at: Optional[datetime] = None       # modifier_le (si modifié après création)
    modified_by: Optional[str] = None            # ID utilisateur modificateur
    modified_by_code: Optional[str] = None       # modifier_par - Code employé

class PriceHistoryCreate(BaseModel):
    product_id: str
    purchase_price: float
    selling_price: float
    change_type: PriceChangeType
    supply_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None

class PriceSummary(BaseModel):
    """Résumé des prix d'un produit"""
    product_id: str
    product_name: str
    product_reference: Optional[str] = None
    current_purchase_price: float
    current_selling_price: float
    price_changes_count: int
    last_change_date: Optional[datetime] = None
    last_modified_by_code: Optional[str] = None
