from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    stock_valuation_method: str = "fefo"  # fifo, lifo, fefo, weighted_average
    currency: str = "GNF"
    pharmacy_name: Optional[str] = None
    low_stock_threshold: int = 10  # Seuil de stock bas (global)
    default_min_stock: int = 10  # Stock minimum par défaut pour les nouveaux produits
    return_delay_days: int = 3  # Délai maximum pour les retours (en jours)
    expiration_alert_days: int = 30  # Délai pour alerter sur les produits à péremption proche (en jours)
    top_debt_customers_count: int = 10  # Nombre de clients dans "Top Clients Endettés"
    # Numéros OTP par défaut pour Mobile Money
    orange_money_default_phone: Optional[str] = None  # Numéro par défaut pour Orange Money OTP
    mtn_money_default_phone: Optional[str] = None  # Numéro par défaut pour MTN Money OTP
    # Durée par défaut du shift en heures
    default_shift_duration_hours: int = 8  # Durée par défaut du shift (8h)
    # Délai en jours après lequel une dette est considérée en retard (si pas de date d'échéance définie)
    debt_overdue_days: int = 90  # Par défaut 90 jours
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SettingsUpdate(BaseModel):
    stock_valuation_method: Optional[str] = None
    currency: Optional[str] = None
    pharmacy_name: Optional[str] = None
    low_stock_threshold: Optional[int] = None
    default_min_stock: Optional[int] = None  # Stock minimum par défaut
    return_delay_days: Optional[int] = None  # Délai maximum pour les retours
    expiration_alert_days: Optional[int] = None  # Délai pour alerter sur les produits à péremption proche
    top_debt_customers_count: Optional[int] = None  # Nombre de clients dans "Top Clients Endettés"
    # Numéros OTP par défaut pour Mobile Money
    orange_money_default_phone: Optional[str] = None
    mtn_money_default_phone: Optional[str] = None
    # Durée par défaut du shift
    default_shift_duration_hours: Optional[int] = None
    # Délai en jours après lequel une dette est considérée en retard
    debt_overdue_days: Optional[int] = None
