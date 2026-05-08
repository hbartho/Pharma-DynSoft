from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, timezone
import uuid

class Product(BaseModel):
    """
    Modèle Produit - Informations de base uniquement
    
    Les champs suivants ont été retirés car gérés par d'autres tables:
    - purchase_price -> Table PRIX (historique des prix via approvisionnement)
    - price -> Table PRIX (prix de vente via approvisionnement)
    - stock -> Table STOCK (calculé depuis les lots par approvisionnement)
    - min_stock -> Table STOCK_CONFIG (configuration par produit)
    - expiration_date -> Table STOCK (date par lot d'approvisionnement)
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    internal_reference: Optional[str] = None  # Référence interne
    barcode: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_id: Optional[str] = None  # Unité de produit (Boîte, Flacon...)
    is_active: bool = True
    # Champs pour PostgreSQL (pas de séparation des tables)
    purchase_price: Optional[float] = 0
    price: Optional[float] = 0
    stock: Optional[int] = 0
    min_stock: Optional[int] = 10
    expiration_date: Optional[datetime] = None
    tenant_id: Optional[str] = "default"  # Optionnel pour PostgreSQL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    """Création d'un produit - sans prix ni stock"""
    name: str
    internal_reference: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_id: Optional[str] = None
    is_active: bool = True

class ProductUpdate(BaseModel):
    """Mise à jour d'un produit - sans prix ni stock"""
    name: Optional[str] = None
    internal_reference: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_id: Optional[str] = None
    is_active: Optional[bool] = None

class ProductWithStock(BaseModel):
    """
    Produit enrichi avec informations de stock et prix calculées
    Utilisé pour l'affichage dans le frontend
    """
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    internal_reference: Optional[str] = None
    barcode: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    unit_id: Optional[str] = None
    is_active: bool = True
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    
    # Champs calculés depuis les tables STOCK et PRIX
    purchase_price: float = 0     # Dernier prix d'achat (depuis PRIX)
    price: float = 0              # Dernier prix de vente (depuis PRIX)
    stock: int = 0                # Stock total (somme des lots depuis STOCK)
    min_stock: int = 10           # Stock minimum (depuis STOCK_CONFIG)
    
    # Informations de péremption (depuis les lots STOCK)
    expiration_date: Optional[datetime] = None  # Date de péremption la plus proche
    lots_count: int = 0           # Nombre de lots actifs
    expired_lots_count: int = 0   # Nombre de lots expirés
