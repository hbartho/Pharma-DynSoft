from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import uuid

class StockMovementType(str, Enum):
    INITIAL = "initial"          # Stock initial
    SUPPLY = "supply"            # Approvisionnement
    SALE = "sale"                # Vente
    RETURN = "return"            # Retour client
    ADJUSTMENT = "adjustment"    # Ajustement manuel
    TRANSFER = "transfer"        # Transfert entre agences

class StockMovement(BaseModel):
    """Historique des mouvements de stock"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: Optional[str] = None  # Dénormalisé pour affichage
    movement_type: StockMovementType
    movement_quantity: int  # Positif pour entrée, négatif pour sortie
    stock_before: int  # Stock avant le mouvement
    stock_after: int   # Stock après le mouvement
    reference_type: Optional[str] = None  # supply, sale, return, adjustment
    reference_id: Optional[str] = None    # ID de la référence
    notes: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None

class StockMovementCreate(BaseModel):
    product_id: str
    movement_type: StockMovementType
    movement_quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    notes: Optional[str] = None

class StockSummary(BaseModel):
    """Résumé du stock d'un produit"""
    product_id: str
    product_name: str
    current_stock: int
    total_entries: int  # Total des entrées
    total_exits: int    # Total des sorties
    last_movement_date: Optional[datetime] = None
    movements_count: int
