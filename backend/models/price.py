from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Any
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
    """Historique des prix d'un produit - Table PRIX
    
    Champs standardisés selon la demande utilisateur:
    - date_maj_prix: Date de mise à jour du prix
    - prix_vente_prod: Prix de vente du produit
    - prix_appro: Prix d'approvisionnement (achat)
    - date_peremption: Date de péremption du produit (optionnel)
    - Traçabilité via employee_code uniquement
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Référence produit
    product_id: str                              # ref_prod (ID)
    product_name: Optional[str] = None           # Nom du produit (dénormalisé)
    product_reference: Optional[str] = None      # ref_prod (référence interne)
    
    # Prix - Champs principaux demandés (avec compatibilité anciens champs)
    prix_appro: float = 0                        # prix_appro - Prix d'approvisionnement/achat
    prix_vente_prod: float = 0                   # prix_vente_prod - Prix de vente du produit
    prix_appro_avant: Optional[float] = None     # Prix achat avant modification
    prix_vente_avant: Optional[float] = None     # Prix vente avant modification
    
    # Dates - Champs principaux demandés
    date_maj_prix: Optional[datetime] = None     # Date mise à jour prix
    date_appro: Optional[datetime] = None        # date_appro - Date de l'approvisionnement
    date_peremption: Optional[datetime] = None   # date_peremption - Date de péremption
    
    # Type et référence
    change_type: PriceChangeType
    reference_type: Optional[str] = None         # supply, manual, category
    reference_id: Optional[str] = None           # ID de la référence (supply_id, etc.)
    notes: Optional[str] = None
    
    # Agence
    tenant_id: str                               # IDAgence
    
    # Traçabilité - Utiliser employee_code (ou user_id pour compatibilité)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""                         # employee_code du créateur (ex: ADM-001)
    
    modified_at: Optional[datetime] = None
    modified_by: Optional[str] = None            # employee_code du modificateur
    
    @model_validator(mode='before')
    @classmethod
    def migrate_old_fields(cls, data: Any) -> Any:
        """Migrer les anciens noms de champs vers les nouveaux"""
        if isinstance(data, dict):
            # Mapper les anciens noms de champs vers les nouveaux
            if 'purchase_price' in data and 'prix_appro' not in data:
                data['prix_appro'] = data.get('purchase_price', 0)
            if 'selling_price' in data and 'prix_vente_prod' not in data:
                data['prix_vente_prod'] = data.get('selling_price', 0)
            if 'purchase_price_before' in data and 'prix_appro_avant' not in data:
                data['prix_appro_avant'] = data.get('purchase_price_before')
            if 'selling_price_before' in data and 'prix_vente_avant' not in data:
                data['prix_vente_avant'] = data.get('selling_price_before')
            if 'price_update_date' in data and 'date_maj_prix' not in data:
                data['date_maj_prix'] = data.get('price_update_date')
            if 'supply_date' in data and 'date_appro' not in data:
                data['date_appro'] = data.get('supply_date')
            if 'expiration_date' in data and 'date_peremption' not in data:
                data['date_peremption'] = data.get('expiration_date')
            # Gérer effective_date également
            if 'effective_date' in data and 'date_maj_prix' not in data:
                data['date_maj_prix'] = data.get('effective_date')
            # Si date_maj_prix est toujours None, utiliser created_at
            if not data.get('date_maj_prix'):
                data['date_maj_prix'] = data.get('created_at', datetime.now(timezone.utc))
            # Assurer que created_by a une valeur par défaut
            if not data.get('created_by'):
                data['created_by'] = data.get('created_by_code', 'N/A')
        return data

class PriceHistoryCreate(BaseModel):
    product_id: str
    prix_appro: float                            # Prix d'achat
    prix_vente_prod: float                       # Prix de vente
    change_type: PriceChangeType
    date_appro: Optional[datetime] = None
    date_peremption: Optional[datetime] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None

class PriceSummary(BaseModel):
    """Résumé des prix d'un produit"""
    product_id: str
    product_name: str
    product_reference: Optional[str] = None
    current_prix_appro: float                    # Prix d'achat actuel
    current_prix_vente: float                    # Prix de vente actuel
    price_changes_count: int
    last_change_date: Optional[datetime] = None
    last_modified_by: Optional[str] = None       # employee_code
