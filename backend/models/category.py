from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Category(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#3B82F6"
    markup_coefficient: float = 1.0  # Coefficient d'intérêt (prix vente = prix achat * coef)
    min_stock: Optional[int] = None  # Stock minimum par catégorie (surcharge le paramètre global)
    tenant_id: Optional[str] = "default"  # Optionnel pour PostgreSQL multi-tenant
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#3B82F6"
    markup_coefficient: float = 1.0
    min_stock: Optional[int] = None  # Stock minimum par catégorie

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    markup_coefficient: Optional[float] = None
    min_stock: Optional[int] = None
