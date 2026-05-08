from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid


class StockLot(BaseModel):
    """
    Lot de stock par approvisionnement - Table STOCK
    Chaque approvisionnement crée un nouveau lot avec sa propre quantité et date de péremption.
    Le stock total d'un produit = somme des quantités de tous ses lots actifs.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Référence produit
    product_id: str
    product_name: Optional[str] = None  # Dénormalisé pour affichage
    
    # Quantités
    initial_quantity: int = 0      # Quantité initiale du lot
    current_quantity: int = 0      # Quantité restante dans le lot
    
    # Prix du lot (au moment de l'approvisionnement)
    purchase_price: float = 0      # Prix d'achat unitaire
    selling_price: float = 0       # Prix de vente unitaire suggéré
    
    # Dates
    expiration_date: Optional[datetime] = None  # Date de péremption du lot
    supply_date: Optional[datetime] = None      # Date d'approvisionnement
    
    # Références
    supply_id: Optional[str] = None             # ID de l'approvisionnement source
    supply_item_id: Optional[str] = None        # ID de l'item dans l'approvisionnement
    supplier_id: Optional[str] = None           # ID du fournisseur
    supplier_name: Optional[str] = None         # Nom du fournisseur (dénormalisé)
    
    # Numéro de lot (optionnel, pour traçabilité)
    lot_number: Optional[str] = None            # Numéro de lot fabricant
    shelf_location: Optional[str] = None        # Rayon/Emplacement de stockage
    tva_rate: float = 0                         # Taux de TVA (%)
    
    # Statut
    is_active: bool = True                      # Lot actif (non épuisé)
    is_expired: bool = False                    # Lot expiré
    
    # Agence
    tenant_id: str
    
    # Traçabilité
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""  # employee_code
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None


class StockLotCreate(BaseModel):
    """Création d'un lot de stock"""
    product_id: str
    initial_quantity: int
    purchase_price: float = 0
    selling_price: float = 0
    expiration_date: Optional[datetime] = None
    supply_date: Optional[datetime] = None
    supply_id: Optional[str] = None
    supply_item_id: Optional[str] = None
    supplier_id: Optional[str] = None
    lot_number: Optional[str] = None


class ProductStockConfig(BaseModel):
    """
    Configuration du stock pour un produit - Seuils et alertes
    Permet de définir le stock minimum par produit.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    product_id: str
    min_stock: int = 10            # Stock minimum (seuil d'alerte)
    max_stock: Optional[int] = None  # Stock maximum (optionnel)
    reorder_quantity: Optional[int] = None  # Quantité à commander
    
    tenant_id: str
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class ProductStockSummary(BaseModel):
    """
    Résumé du stock d'un produit (calculé depuis les lots)
    """
    product_id: str
    product_name: str
    
    # Stock calculé
    total_stock: int = 0           # Somme des quantités de tous les lots
    lots_count: int = 0            # Nombre de lots actifs
    
    # Prix actuels (du lot le plus récent ou moyenne pondérée)
    current_purchase_price: float = 0
    current_selling_price: float = 0
    
    # Alertes
    min_stock: int = 10
    needs_restock: bool = False
    
    # Dates de péremption
    nearest_expiration: Optional[datetime] = None
    expired_lots_count: int = 0
    near_expiration_lots_count: int = 0
