from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid

class SplitPayment(BaseModel):
    """Représente un paiement individuel dans une vente à paiements multiples"""
    method: str  # Code du mode de paiement (cash, orange_money, mtn_money, card, check, debt)
    amount: float  # Montant de ce paiement
    details: Optional[Dict[str, Any]] = None  # Détails spécifiques (N° expéditeur, réf. ticket, etc.)

class Sale(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sale_number: Optional[str] = None  # Numéro de vente lisible (ex: VNT-001)
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None  # Dénormalisé pour affichage
    items: List[Dict[str, Any]]
    subtotal: Optional[float] = None  # Sous-total avant rabais
    discount_type: Optional[str] = None  # 'percent' ou 'amount'
    discount_value: Optional[float] = 0  # Valeur du rabais (% ou montant)
    discount_amount: Optional[float] = 0  # Montant du rabais calculé
    total: float  # Total TTC
    total_ht: Optional[float] = None  # Total HT (hors TVA)
    tva_total: Optional[float] = 0  # Montant total TVA
    # Paiement principal (pour rétro-compatibilité)
    payment_method: str  # 'mixed' si paiement multiple, sinon le code du mode unique
    payment_details: Optional[Dict[str, Any]] = None  # Détails pour paiement unique
    # Paiements multiples (relation 1..*)
    is_split_payment: bool = False  # True si la vente utilise plusieurs modes de paiement
    split_payments: Optional[List[Dict[str, Any]]] = None  # Liste des paiements [{method, amount, details}]
    # Paiement avec dette
    amount_paid: Optional[float] = None  # Montant payé directement
    debt_amount: Optional[float] = None  # Montant en dette
    has_debt: bool = False  # Indique si la vente a une dette associée
    debt_id: Optional[str] = None  # Référence vers la dette créée
    valuation_method: Optional[str] = None  # Méthode de valorisation utilisée (FIFO/LIFO/FEFO/CMP)
    tenant_id: str
    user_id: Optional[str] = None
    employee_code: Optional[str] = None  # Code employé du vendeur
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SaleCreate(BaseModel):
    customer_id: Optional[str] = None
    items: List[Dict[str, Any]]
    subtotal: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = 0
    discount_amount: Optional[float] = 0
    # Code promo
    promo_code: Optional[str] = None
    promo_discount_amount: Optional[float] = 0
    # Rabais automatiques
    automatic_discounts: Optional[List[Dict[str, Any]]] = None
    automatic_discount_amount: Optional[float] = 0
    # Total des rabais
    total_discount_amount: Optional[float] = 0
    total: float
    payment_method: str
    payment_details: Optional[Dict[str, Any]] = None
    # Paiements multiples (optionnel)
    is_split_payment: Optional[bool] = False
    split_payments: Optional[List[Dict[str, Any]]] = None
    # Paiement mixte (optionnel)
    amount_paid: Optional[float] = None  # Montant payé immédiatement
    debt_amount: Optional[float] = None  # Montant en dette
