from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid

class SupplyItem(BaseModel):
    """Détail d'un approvisionnement (ligne de produit)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    product_name: Optional[str] = None  # Dénormalisé pour affichage
    quantity: int
    unit_price: float  # Prix d'achat unitaire
    total_price: float = 0  # quantity * unit_price
    # Champs optionnels pour l'historique des prix
    date_peremption: Optional[datetime] = None  # Date de péremption du lot

class Supply(BaseModel):
    """Approvisionnement / Entrée de stock"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supply_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # date_appro
    is_validated: bool = False  # validerAppro - En attente par défaut
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None  # employee_code du validateur (ex: ADM-001)
    supplier_id: Optional[str] = None  # IDFournisseur
    supplier_name: Optional[str] = None  # Dénormalisé
    total_amount: float = 0  # MontantAppro
    purchase_order_ref: Optional[str] = None  # Ref_Bon_commande
    delivery_note_number: Optional[str] = None  # Num_Bon_Livraison
    invoice_number: Optional[str] = None  # num_fact
    is_credit_note: bool = False  # avoir
    notes: Optional[str] = None
    items: List[SupplyItem] = []  # Details_Appro
    tenant_id: str  # IDAgence
    
    # Traçabilité - Utiliser UNIQUEMENT employee_code
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""  # employee_code du créateur (ex: ADM-001, PHA-001)
    
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None  # employee_code du modificateur

class SupplyItemCreate(BaseModel):
    product_id: str
    quantity: int
    unit_price: float
    date_peremption: Optional[datetime] = None  # Date de péremption optionnelle

class SupplyCreate(BaseModel):
    supply_date: Optional[datetime] = None
    supplier_id: Optional[str] = None
    purchase_order_ref: Optional[str] = None
    delivery_note_number: Optional[str] = None
    invoice_number: Optional[str] = None
    is_credit_note: bool = False
    notes: Optional[str] = None
    items: List[SupplyItemCreate] = []

class SupplyItemUpdate(BaseModel):
    product_id: str
    quantity: int
    unit_price: float
    date_peremption: Optional[datetime] = None

class SupplyUpdate(BaseModel):
    supply_date: Optional[datetime] = None
    supplier_id: Optional[str] = None
    purchase_order_ref: Optional[str] = None
    delivery_note_number: Optional[str] = None
    invoice_number: Optional[str] = None
    is_credit_note: bool = False
    notes: Optional[str] = None
    items: List[SupplyItemUpdate] = []
