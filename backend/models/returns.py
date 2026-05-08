from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class SaleReturn(BaseModel):
    """Modèle pour les retours de vente"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    return_number: Optional[str] = None  # Numéro de retour lisible (ex: RET-001)
    
    # Référence à la vente originale
    sale_id: str                          # ID de la vente
    sale_number: Optional[str] = None     # Numéro de vente lisible (ex: VNT-001)
    
    # Détails du retour
    items: List[Dict[str, Any]]  # [{product_id, name, quantity, price, refund}]
    total_refund: float
    reason: Optional[str] = None
    
    # Traçabilité - Utiliser employee_code
    user_id: str
    employee_code: Optional[str] = None   # Code employé qui a fait le retour (ex: CAI-001)
    
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SaleReturnCreate(BaseModel):
    sale_id: str
    items: List[Dict[str, Any]]  # [{product_id, quantity}]
    reason: str  # Motif obligatoire
