from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    stock_valuation_method: str = "weighted_average"  # fifo, lifo, weighted_average
    currency: str = "GNF"
    pharmacy_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SettingsUpdate(BaseModel):
    stock_valuation_method: Optional[str] = None
    currency: Optional[str] = None
    pharmacy_name: Optional[str] = None
