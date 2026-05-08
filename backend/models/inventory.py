from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone
import uuid


class InventoryItem(BaseModel):
    """Un article dans une session d'inventaire"""
    product_id: str
    product_name: str
    barcode: Optional[str] = None
    category_name: Optional[str] = None
    theoretical_quantity: int = 0  # Stock théorique (système)
    actual_quantity: Optional[int] = None  # Stock réel (compté)
    discrepancy: Optional[int] = None  # Écart (réel - théorique)
    discrepancy_value: Optional[float] = None  # Valeur de l'écart en GNF
    unit_cost: float = 0  # Prix unitaire pour calcul valeur
    note: Optional[str] = None  # Note explicative pour l'écart
    counted_at: Optional[datetime] = None  # Heure du comptage
    counted_by: Optional[str] = None  # Code employé qui a compté


class InventorySessionCreate(BaseModel):
    """Données pour créer une session d'inventaire"""
    name: Optional[str] = None  # Nom optionnel (ex: "Inventaire Janvier 2026")
    category_id: Optional[str] = None  # Filtrer par catégorie (None = tous)
    notes: Optional[str] = None


class InventoryItemUpdate(BaseModel):
    """Mise à jour d'un article d'inventaire"""
    actual_quantity: int = Field(..., ge=0)
    note: Optional[str] = None


class InventorySession(BaseModel):
    """Session d'inventaire"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    status: str = "in_progress"  # in_progress, completed, cancelled
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    
    # Statistiques
    total_products: int = 0
    counted_products: int = 0
    products_with_discrepancy: int = 0
    total_positive_discrepancy: int = 0  # Excédents
    total_negative_discrepancy: int = 0  # Manques
    total_discrepancy_value: float = 0  # Valeur totale des écarts
    
    # Articles
    items: List[InventoryItem] = []
    
    # Métadonnées
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    created_by_name: str = ""
    completed_at: Optional[datetime] = None
    completed_by: Optional[str] = None
    validated_by: Optional[str] = None
    notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class InventoryValidation(BaseModel):
    """Validation d'une session d'inventaire"""
    apply_adjustments: bool = True  # Appliquer les ajustements au stock
    validation_notes: Optional[str] = None
