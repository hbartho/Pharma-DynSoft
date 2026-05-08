from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid


class Shift(BaseModel):
    """Modèle pour la gestion des shifts de caisse"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    user_id: str
    user_name: str  # Nom du caissier pour affichage
    employee_code: str  # Code employé
    
    # Horaires
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expected_end_time: Optional[datetime] = None  # Heure de fin prévue du shift
    closed_at: Optional[datetime] = None
    
    # Montants
    opening_amount: float  # Fond de caisse au début du shift
    expected_closing_amount: Optional[float] = None  # Calculé: opening + ventes espèces
    actual_closing_amount: Optional[float] = None  # Montant compté par le caissier
    difference: Optional[float] = None  # Écart (actual - expected)
    
    # Statistiques du shift
    total_cash_sales: float = 0  # Total des ventes en espèces
    total_sales_count: int = 0  # Nombre de ventes
    sales_ids: List[str] = []  # IDs des ventes du shift
    
    # Statut et notes
    status: str = "open"  # open, closed
    closing_notes: Optional[str] = None  # Notes en cas d'écart
    has_discrepancy: bool = False  # True si écart détecté
    
    # Alertes de fin de shift
    alert_30min_shown: bool = False  # Alerte 30min affichée
    alert_5min_shown: bool = False   # Alerte 5min affichée
    alert_end_shown: bool = False    # Alerte fin de shift affichée
    

class ShiftOpen(BaseModel):
    """Données pour ouvrir un shift"""
    opening_amount: float = Field(..., ge=0, description="Fond de caisse initial")
    expected_end_time: Optional[str] = None  # Format ISO ou HH:MM


class ShiftClose(BaseModel):
    """Données pour clôturer un shift"""
    actual_closing_amount: float = Field(..., ge=0, description="Montant compté en caisse")
    closing_notes: Optional[str] = None  # Notes explicatives si écart


class ShiftSummary(BaseModel):
    """Résumé d'un shift pour l'affichage"""
    id: str
    user_name: str
    employee_code: str
    opened_at: datetime
    closed_at: Optional[datetime]
    opening_amount: float
    total_cash_sales: float
    expected_closing_amount: Optional[float]
    actual_closing_amount: Optional[float]
    difference: Optional[float]
    has_discrepancy: bool
    status: str
    total_sales_count: int
