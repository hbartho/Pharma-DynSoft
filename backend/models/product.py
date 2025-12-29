from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    price: float
    stock: int
    min_stock: int = 10
    category_id: Optional[str] = None
    is_active: bool = True
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    price: float
    stock: int
    min_stock: int = 10
    category_id: Optional[str] = None
    is_active: bool = True
