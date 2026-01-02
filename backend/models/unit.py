from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Unit(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # Ex: Boîte, Flacon, Comprimé, Tube, Sachet...
    abbreviation: Optional[str] = None  # Ex: BTE, FLC, CPR, TUB, SCH...
    description: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UnitCreate(BaseModel):
    name: str
    abbreviation: Optional[str] = None
    description: Optional[str] = None
