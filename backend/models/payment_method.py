from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid


class PaymentMethod(BaseModel):
    """Modèle pour les modes de paiement"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str  # ex: 'cash', 'orange_money', 'card', 'check'
    name: str  # ex: 'Espèces', 'Orange Money', 'Carte bancaire', 'Chèque'
    icon: Optional[str] = None  # ex: 'banknote', 'smartphone', 'credit-card', 'file-check'
    color: Optional[str] = None  # ex: 'green', 'orange', 'purple', 'blue'
    required_fields: List[Dict[str, Any]] = []  # Champs requis pour ce mode
    # Format: [{"name": "sender_number", "label": "N° Expéditeur", "type": "tel", "placeholder": "620 00 00 00"}]
    is_active: bool = True
    display_order: int = 0
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class PaymentMethodCreate(BaseModel):
    """Modèle pour créer un mode de paiement"""
    code: str
    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    required_fields: List[Dict[str, Any]] = []
    is_active: bool = True
    display_order: int = 0


class PaymentMethodUpdate(BaseModel):
    """Modèle pour mettre à jour un mode de paiement"""
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    required_fields: Optional[List[Dict[str, Any]]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class SalePayment(BaseModel):
    """Modèle pour les paiements d'une vente (permet paiements multiples)"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sale_id: str
    payment_method_id: str
    payment_method_code: Optional[str] = None  # Pour faciliter l'affichage
    payment_method_name: Optional[str] = None
    amount: float
    details: Optional[Dict[str, Any]] = None  # Détails spécifiques au mode de paiement
    status: str = "completed"  # pending, completed, failed, refunded
    reference: Optional[str] = None  # Référence externe (ticket, n° chèque, etc.)
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None


class SalePaymentCreate(BaseModel):
    """Modèle pour créer un paiement"""
    sale_id: str
    payment_method_id: str
    amount: float
    details: Optional[Dict[str, Any]] = None
    status: str = "completed"
    reference: Optional[str] = None
