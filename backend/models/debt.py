from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid


class Debt(BaseModel):
    """Modèle pour les dettes clients (créances)"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    customer_name: Optional[str] = None  # Dénormalisé pour affichage
    sale_id: str  # Vente qui a généré cette dette
    sale_number: Optional[str] = None  # Numéro de vente pour référence
    
    # Montants
    original_amount: float  # Montant initial de la dette
    remaining_amount: float  # Montant restant à payer
    
    # Statut: pending, partial, paid, abandoned (passé en perte)
    status: str = "pending"
    
    # Champs pour abandon/passage en perte
    abandoned_at: Optional[datetime] = None
    abandoned_by: Optional[str] = None
    abandoned_by_name: Optional[str] = None
    abandon_reason: Optional[str] = None
    
    # Métadonnées
    notes: Optional[str] = None
    due_date: Optional[datetime] = None  # Date d'échéance optionnelle
    
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class DebtCreate(BaseModel):
    """Modèle pour créer une dette"""
    customer_id: str
    sale_id: str
    original_amount: float
    notes: Optional[str] = None
    due_date: Optional[datetime] = None


class DebtPayment(BaseModel):
    """Modèle pour les remboursements de dette"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    debt_id: str
    customer_id: str
    customer_name: Optional[str] = None
    
    # Montant du remboursement
    amount: float
    
    # Mode de paiement: cash, card, orange_money, mtn_money, check, write_off (passage en perte)
    payment_method: str = "cash"
    payment_details: Optional[dict] = None
    
    # Type de transaction: payment (remboursement normal), write_off (abandon/perte)
    transaction_type: str = "payment"
    
    # Référence
    reference: Optional[str] = None  # Numéro de reçu
    notes: Optional[str] = None
    
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None


class DebtPaymentCreate(BaseModel):
    """Modèle pour créer un remboursement"""
    debt_id: str
    amount: float
    payment_method: str = "cash"
    payment_details: Optional[dict] = None
    reference: Optional[str] = None
    notes: Optional[str] = None


class CustomerDebtSummary(BaseModel):
    """Résumé des dettes d'un client"""
    customer_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    max_debt_limit: float = 0
    total_debt: float = 0
    available_credit: float = 0
    debts_count: int = 0
    oldest_debt_date: Optional[datetime] = None
    last_payment_date: Optional[datetime] = None


class DebtDashboardStats(BaseModel):
    """Statistiques du dashboard des dettes"""
    total_receivables: float = 0  # Total des créances
    total_customers_with_debt: int = 0  # Nombre de clients endettés
    overdue_amount: float = 0  # Montant en retard (si due_date dépassée)
    overdue_count: int = 0  # Nombre de dettes en retard
    collected_this_month: float = 0  # Remboursements du mois
    average_debt_per_customer: float = 0
    # Stats des abandons
    written_off_this_month: float = 0  # Montant passé en perte ce mois
    written_off_count: int = 0  # Nombre de dettes abandonnées ce mois
