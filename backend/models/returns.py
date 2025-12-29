from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class SaleReturn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sale_id: str
    items: List[Dict[str, Any]]  # [{product_id, name, quantity, price}]
    total_refund: float
    reason: Optional[str] = None
    user_id: str
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SaleReturnCreate(BaseModel):
    sale_id: str
    items: List[Dict[str, Any]]  # [{product_id, quantity}]
    reason: str  # Motif obligatoire
