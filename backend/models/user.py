from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    first_name: str  # Prénom
    last_name: str   # Nom
    employee_code: str  # Code employé
    role: str  # admin, pharmacien, caissier
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    employee_code: str
    role: str
    tenant_id: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    employee_code: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    first_name: str
    last_name: str
    employee_code: str
    role: str
    tenant_id: str
    is_active: bool = True
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User
