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
    
    # Nouveaux champs
    date_peremption: Optional[datetime] = None  # Date de péremption du lot
    lot_number: Optional[str] = None  # Numéro de lot fabricant
    shelf_location: Optional[str] = None  # Rayon/Emplacement
    tva_rate: float = 0  # Taux de TVA (%)
    
    # Champs calculés/récupérés (pour affichage)
    current_stock: Optional[int] = None  # Stock actuel (récupéré)
    markup_coefficient: Optional[float] = None  # Coefficient d'intérêt (récupéré de la catégorie)
    selling_price: Optional[float] = None  # Prix de vente final (modifié ou base)
    prix_public_base: Optional[float] = None  # Prix public calculé (unit_price × coefficient)
    prix_public_modifie: Optional[float] = None  # Prix public modifié (optionnel)
    prix_ttc: Optional[float] = None  # Prix TTC (prix_public_base × (1 + TVA))
    category_name: Optional[str] = None  # Nom de la catégorie

class Supply(BaseModel):
    """Approvisionnement / Entrée de stock"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    supply_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))  # date_appro
    is_validated: bool = False  # validerAppro - En attente par défaut
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None  # employee_code du validateur (ex: ADM-001)
    validated_by_name: Optional[str] = None  # Code employé enrichi
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
    created_by_name: Optional[str] = None  # Code employé enrichi
    
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None  # employee_code du modificateur
    updated_by_name: Optional[str] = None  # Code employé enrichi

class SupplyItemCreate(BaseModel):
    product_id: str
    quantity: int
    unit_price: float  # Prix de cession (achat)
    selling_price: Optional[float] = None  # Prix public modifié (optionnel)
    prix_public_modifie: Optional[float] = None  # Alias pour clarté
    date_peremption: Optional[datetime] = None  # Date de péremption
    expiration_date: Optional[datetime] = None  # Alias
    lot_number: Optional[str] = None  # Numéro de lot
    shelf_location: Optional[str] = None  # Rayon/Emplacement
    rayon: Optional[str] = None  # Alias pour shelf_location
    tva_rate: float = 0  # Taux de TVA (%)
    tva: Optional[float] = None  # Alias pour tva_rate
    tax_rate: Optional[float] = None  # Alias pour tva_rate

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
    lot_number: Optional[str] = None
    shelf_location: Optional[str] = None
    tva_rate: float = 0
    prix_public_modifie: Optional[float] = None  # Prix public modifié (optionnel)

class SupplyUpdate(BaseModel):
    supply_date: Optional[datetime] = None
    supplier_id: Optional[str] = None
    purchase_order_ref: Optional[str] = None
    delivery_note_number: Optional[str] = None
    invoice_number: Optional[str] = None
    is_credit_note: bool = False
    notes: Optional[str] = None
    items: List[SupplyItemUpdate] = []
