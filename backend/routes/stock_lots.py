"""
Routes Stock Lots - PostgreSQL Implementation
Gère les lots de stock via supply_items
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
import uuid
import os

from auth import require_role, get_current_user

router = APIRouter(prefix="/stock-lots", tags=["stock-lots"])

class StockLotUpdate(BaseModel):
    """Mise à jour d'un lot de stock"""
    selling_price: Optional[float] = None
    purchase_price: Optional[float] = None
    lot_number: Optional[str] = None
    shelf_location: Optional[str] = None

class StockLotResponse(BaseModel):
    """Réponse lot de stock"""
    id: str
    product_id: str
    product_name: Optional[str] = None
    initial_quantity: int = 0
    current_quantity: int = 0
    purchase_price: float = 0
    selling_price: float = 0
    expiration_date: Optional[str] = None
    supply_date: Optional[str] = None
    supply_id: Optional[str] = None
    supplier_name: Optional[str] = None

DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import SupplyItem, Supply, Product
    from sqlalchemy import desc
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def lot_to_dict(item, supply=None, product=None, supplier=None) -> dict:
        """Convertir un supply_item en lot de stock"""
        return {
            "id": str(item.id),
            "product_id": str(item.product_id),
            "product_name": item.product_name or (product.name if product else "Inconnu"),
            "initial_quantity": item.quantity,
            "current_quantity": item.quantity,  # Simplifié
            "purchase_price": item.purchase_price or 0,
            "selling_price": item.selling_price or 0,
            "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
            "supply_date": supply.supply_date.isoformat() if supply and supply.supply_date else None,
            "supply_id": str(item.supply_id) if item.supply_id else None,
            "supplier_name": supplier.name if supplier else None,
            "supplier_id": str(supply.supplier_id) if supply and supply.supplier_id else None,
            "lot_number": None,  # Pas de numéro de lot dans ce modèle
            "tenant_id": "pharmacie_centrale"
        }
    
    @router.get("", response_model=List[dict])
    async def get_stock_lots(
        product_id: Optional[str] = None,
        include_empty: bool = False,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les lots de stock"""
        with get_session() as session:
            query = session.query(SupplyItem).join(Supply).join(Product)
            
            if product_id:
                try:
                    query = query.filter(SupplyItem.product_id == uuid.UUID(product_id))
                except ValueError:
                    pass
            
            if not include_empty:
                query = query.filter(SupplyItem.quantity > 0)
            
            items = query.order_by(desc(Supply.supply_date)).limit(500).all()
            
            # Récupérer les infos associées
            result = []
            for item in items:
                supply = item.supply
                product = item.product
                supplier = supply.supplier if supply else None
                result.append(lot_to_dict(item, supply, product, supplier))
            
            return result
    
    @router.get("/{lot_id}", response_model=dict)
    async def get_stock_lot(
        lot_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer un lot par ID"""
        with get_session() as session:
            try:
                item = session.query(SupplyItem).filter(SupplyItem.id == uuid.UUID(lot_id)).first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Lot non trouvé")
            
            if not item:
                raise HTTPException(status_code=404, detail="Lot non trouvé")
            
            return lot_to_dict(item, item.supply, item.product, item.supply.supplier if item.supply else None)
    
    @router.put("/{lot_id}", response_model=dict)
    async def update_stock_lot(
        lot_id: str,
        update_data: StockLotUpdate,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour un lot"""
        with get_session() as session:
            try:
                item = session.query(SupplyItem).filter(SupplyItem.id == uuid.UUID(lot_id)).first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Lot non trouvé")
            
            if not item:
                raise HTTPException(status_code=404, detail="Lot non trouvé")
            
            # Mettre à jour les champs
            if update_data.selling_price is not None:
                item.selling_price = update_data.selling_price
            if update_data.purchase_price is not None:
                item.purchase_price = update_data.purchase_price
            
            session.commit()
            session.refresh(item)
            
            return lot_to_dict(item, item.supply, item.product, item.supply.supplier if item.supply else None)
    
    @router.get("/by-supply/{supply_id}", response_model=List[dict])
    async def get_lots_by_supply(
        supply_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les lots d'un approvisionnement"""
        with get_session() as session:
            try:
                items = session.query(SupplyItem).filter(
                    SupplyItem.supply_id == uuid.UUID(supply_id)
                ).join(Supply).all()
            except ValueError:
                return []
            
            return [lot_to_dict(item, item.supply, item.product, item.supply.supplier if item.supply else None) for item in items]

    @router.put("/bulk-update", response_model=dict)
    async def bulk_update_lots(
        updates: List[dict],
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour plusieurs lots en une seule requête"""
        updated = []
        errors = []
        
        with get_session() as session:
            for idx, update_data in enumerate(updates):
                try:
                    lot_id = update_data.get("id")
                    if not lot_id:
                        errors.append({"index": idx, "error": "ID manquant"})
                        continue
                    
                    item = session.query(SupplyItem).filter(
                        SupplyItem.id == uuid.UUID(lot_id)
                    ).first()
                    
                    if not item:
                        errors.append({"index": idx, "error": f"Lot {lot_id} non trouvé"})
                        continue
                    
                    # Mettre à jour les champs
                    if "lot_number" in update_data:
                        item.lot_number = update_data["lot_number"]
                    if "expiration_date" in update_data:
                        item.expiration_date = update_data["expiration_date"]
                    if "quantity" in update_data:
                        item.quantity = update_data["quantity"]
                    
                    updated.append(str(lot_id))
                except Exception as e:
                    errors.append({"index": idx, "error": str(e)})
            
            session.commit()
        
        return {
            "message": f"{len(updated)} lot(s) mis à jour",
            "updated": updated,
            "errors": errors
        }

    @router.get("/product/{product_id}/lots", response_model=List[dict])
    async def get_product_lots(
        product_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les lots d'un produit"""
        with get_session() as session:
            try:
                items = session.query(SupplyItem).filter(
                    SupplyItem.product_id == uuid.UUID(product_id)
                ).join(Supply).order_by(desc(Supply.supply_date)).all()
            except ValueError:
                return []
            
            return [lot_to_dict(item, item.supply, item.product, item.supply.supplier if item.supply else None) for item in items]
    
    @router.get("/expiring", response_model=List[dict])
    async def get_expiring_lots(
        days: int = 90,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les lots qui expirent bientôt"""
        from datetime import timedelta
        
        with get_session() as session:
            deadline = datetime.now().date() + timedelta(days=days)
            
            items = session.query(SupplyItem).filter(
                SupplyItem.expiration_date <= deadline,
                SupplyItem.expiration_date >= datetime.now().date(),
                SupplyItem.quantity > 0
            ).join(Supply).order_by(SupplyItem.expiration_date).all()
            
            return [lot_to_dict(item, item.supply, item.product, item.supply.supplier if item.supply else None) for item in items]

