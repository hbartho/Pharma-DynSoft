from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Customer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True  # Statut actif/inactif du client
    # Gestion des dettes
    max_debt_limit: float = 0  # Seuil maximum de dette autorisé (0 = pas de crédit)
    current_debt: float = 0  # Dette actuelle (calculé, dénormalisé pour performance)
    tenant_id: Optional[str] = "default"  # Optionnel pour PostgreSQL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    max_debt_limit: float = 0  # Seuil de dette (0 par défaut = pas de crédit)

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    max_debt_limit: Optional[float] = None
