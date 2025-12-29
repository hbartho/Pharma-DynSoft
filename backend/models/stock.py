from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class StockMovement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    type: str  # in, out
    quantity: int
    unit_price: float = 0.0
    remaining_quantity: int = 0
    reason: Optional[str] = None
    supplier_id: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StockMovementCreate(BaseModel):
    product_id: str
    type: str
    quantity: int
    unit_price: float = 0.0
    reason: Optional[str] = None
    supplier_id: Optional[str] = None
