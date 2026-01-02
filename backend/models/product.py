from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    internal_reference: Optional[str] = None  # Référence interne
    barcode: Optional[str] = None
    description: Optional[str] = None
    purchase_price: float = 0  # Prix d'achat (fournisseur)
    price: float  # Prix de vente
    stock: int
    min_stock: int = 10
    category_id: Optional[str] = None
    unit_id: Optional[str] = None  # Unité de produit (Boîte, Flacon...)
    is_active: bool = True
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    internal_reference: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    purchase_price: float = 0
    price: float
    stock: int
    min_stock: int = 10
    category_id: Optional[str] = None
    unit_id: Optional[str] = None
    is_active: bool = True
