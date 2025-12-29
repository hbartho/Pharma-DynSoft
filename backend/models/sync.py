from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid

class SyncLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    action: str
    payload: Dict[str, Any]
    tenant_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced: bool = False

class SyncData(BaseModel):
    changes: List[Dict[str, Any]]
