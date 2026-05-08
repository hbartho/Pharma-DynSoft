from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class PendingSale(BaseModel):
    """Vente en attente - n'affecte pas le stock jusqu'à finalisation"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    reference: Optional[str] = None  # Référence courte (ex: ATT-001)
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None  # Dénormalisé pour affichage
    items: List[Dict[str, Any]]  # Liste des produits dans le panier
    subtotal: Optional[float] = None
    discount_type: Optional[str] = None  # 'percent' ou 'amount'
    discount_value: Optional[float] = 0
    discount_amount: Optional[float] = 0
    total: float
    notes: Optional[str] = None  # Notes sur la vente en attente
    
    # Métadonnées
    tenant_id: str
    created_by: str  # ID de l'utilisateur qui a créé la vente en attente
    created_by_name: Optional[str] = None  # Nom de l'utilisateur
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = None  # Date d'expiration (24h après création)
    
    # Statut
    status: str = "pending"  # pending, completed, expired, cancelled


class PendingSaleCreate(BaseModel):
    """Données pour créer une vente en attente"""
    customer_id: Optional[str] = None
    items: List[Dict[str, Any]]
    subtotal: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = 0
    discount_amount: Optional[float] = 0
    total: float
    notes: Optional[str] = None


class PendingSaleUpdate(BaseModel):
    """Données pour mettre à jour une vente en attente"""
    customer_id: Optional[str] = None
    items: Optional[List[Dict[str, Any]]] = None
    subtotal: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    discount_amount: Optional[float] = None
    total: Optional[float] = None
    notes: Optional[str] = None
