from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, timezone, date, time
import uuid


class ShiftSchedule(BaseModel):
    """Planification d'un shift pour un utilisateur"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    
    # Utilisateur planifié
    user_id: str
    user_name: Optional[str] = None  # Dénormalisé pour affichage
    employee_code: Optional[str] = None  # Code employé
    
    # Date et horaires planifiés
    scheduled_date: str  # Format YYYY-MM-DD
    start_time: str  # Format HH:MM
    end_time: str  # Format HH:MM
    max_duration_hours: float = 8.0  # Durée maximale autorisée
    
    # Métadonnées
    notes: Optional[str] = None
    created_by: str  # Admin qui a créé la planification
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    # Statut
    is_active: bool = True


class ShiftScheduleCreate(BaseModel):
    """Données pour créer une planification de shift"""
    user_id: str
    scheduled_date: str  # Format YYYY-MM-DD
    start_time: str  # Format HH:MM
    end_time: str  # Format HH:MM
    max_duration_hours: Optional[float] = 8.0
    notes: Optional[str] = None
    
    @validator('scheduled_date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Format de date invalide. Utilisez YYYY-MM-DD')
        return v
    
    @validator('start_time', 'end_time')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, '%H:%M')
        except ValueError:
            raise ValueError('Format d\'heure invalide. Utilisez HH:MM')
        return v


class ShiftScheduleUpdate(BaseModel):
    """Données pour modifier une planification"""
    scheduled_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    max_duration_hours: Optional[float] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ShiftScheduleBulkCreate(BaseModel):
    """Création de planifications en masse (pour une semaine)"""
    user_id: str
    schedules: List[dict]  # Liste de {scheduled_date, start_time, end_time, max_duration_hours}
    notes: Optional[str] = None


class ShiftEligibility(BaseModel):
    """Résultat de la vérification d'éligibilité pour ouvrir un shift"""
    is_eligible: bool
    reason: Optional[str] = None
    schedule: Optional[dict] = None  # Détails de la planification si trouvée
    suggested_end_time: Optional[str] = None  # Heure de fin suggérée
    max_duration_hours: Optional[float] = None
    current_time: Optional[str] = None  # Heure locale actuelle (pour debug/affichage)
