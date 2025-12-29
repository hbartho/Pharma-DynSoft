from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class Prescription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    doctor_name: str
    medications: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None
    status: str  # pending, fulfilled
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PrescriptionCreate(BaseModel):
    customer_id: str
    doctor_name: str
    medications: List[Dict[str, Any]]
    notes: Optional[str] = None
    status: str = "pending"
