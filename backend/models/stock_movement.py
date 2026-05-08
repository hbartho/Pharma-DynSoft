"""
Modèles pour les mouvements de stock et gestion des pertes
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid


class StockMovement(BaseModel):
    """Modèle pour un mouvement de stock"""
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Produit concerné
    product_id: str
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    
    # Type de mouvement
    # IN: Entrée (achat, retour client)
    # OUT: Sortie (vente, perte, don)
    # ADJUST: Ajustement inventaire
    movement_type: str  # IN, OUT, ADJUST
    
    # Raison du mouvement
    # IN: purchase, customer_return, initial_stock, adjustment_plus
    # OUT: sale, loss, breakage, expiry, donation, theft, counting_error, adjustment_minus, other
    reason: str
    reason_details: Optional[str] = None  # Pour "other" ou détails supplémentaires
    
    # Quantités
    quantity: int  # Toujours positif, le type détermine le sens
    quantity_before: Optional[int] = None  # Stock avant mouvement
    quantity_after: Optional[int] = None   # Stock après mouvement
    
    # Valorisation
    unit_cost: Optional[float] = None
    total_value: Optional[float] = None
    
    # Traçabilité lot/péremption
    lot_number: Optional[str] = None
    expiry_date: Optional[datetime] = None
    
    # Référence externe
    reference_type: Optional[str] = None  # sale, purchase_order, loss_declaration
    reference_id: Optional[str] = None    # ID de la vente, commande, etc.
    reference_number: Optional[str] = None  # Numéro lisible (VNT-001, etc.)
    
    # Pour les pertes : workflow de validation
    requires_validation: bool = False
    status: str = "validated"  # pending, validated, rejected
    validated_by: Optional[str] = None
    validated_by_name: Optional[str] = None
    validated_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Notes
    notes: Optional[str] = None
    
    # Métadonnées
    tenant_id: str
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class StockMovementCreate(BaseModel):
    """Requête pour créer un mouvement de stock"""
    product_id: str
    movement_type: str  # IN, OUT, ADJUST
    reason: str
    reason_details: Optional[str] = None
    quantity: int
    unit_cost: Optional[float] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None


class LossDeclaration(BaseModel):
    """Requête pour déclarer une perte"""
    product_id: str
    quantity: int
    reason: str  # breakage, expiry, theft, counting_error, other
    reason_details: Optional[str] = None
    lot_number: Optional[str] = None
    expiry_date: Optional[str] = None
    notes: Optional[str] = None


class LossValidation(BaseModel):
    """Requête pour valider/rejeter une perte"""
    action: str  # validate, reject
    rejection_reason: Optional[str] = None


# Constantes pour les types et raisons
MOVEMENT_TYPES = ["IN", "OUT", "ADJUST"]

MOVEMENT_REASONS = {
    "IN": [
        {"code": "purchase", "label": "Achat fournisseur"},
        {"code": "customer_return", "label": "Retour client"},
        {"code": "initial_stock", "label": "Stock initial"},
        {"code": "adjustment_plus", "label": "Ajustement positif"},
        {"code": "other_in", "label": "Autre entrée"},
    ],
    "OUT": [
        {"code": "sale", "label": "Vente"},
        {"code": "loss", "label": "Perte"},
        {"code": "breakage", "label": "Casse"},
        {"code": "expiry", "label": "Péremption"},
        {"code": "donation", "label": "Don"},
        {"code": "theft", "label": "Vol"},
        {"code": "counting_error", "label": "Erreur de comptage"},
        {"code": "adjustment_minus", "label": "Ajustement négatif"},
        {"code": "other_out", "label": "Autre sortie"},
    ],
    "ADJUST": [
        {"code": "inventory_adjustment", "label": "Ajustement inventaire"},
        {"code": "correction", "label": "Correction"},
    ]
}

# Raisons qui nécessitent une validation admin
REASONS_REQUIRING_VALIDATION = ["loss", "breakage", "expiry", "theft", "counting_error", "other_out"]


class StockMovementStats(BaseModel):
    """Statistiques des mouvements de stock"""
    total_in: int = 0
    total_out: int = 0
    total_adjustments: int = 0
    value_in: float = 0
    value_out: float = 0
    pending_losses: int = 0
    pending_losses_value: float = 0
