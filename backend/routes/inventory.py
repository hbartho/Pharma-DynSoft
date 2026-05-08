"""
Inventory Routes - PostgreSQL Implementation with Database Persistence
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid

from auth import get_current_user, require_role
from models.inventory import (
    InventorySessionCreate, 
    InventoryItemUpdate,
    InventoryValidation
)

router = APIRouter(prefix="/inventory", tags=["Inventory"])

# PostgreSQL Implementation
from database.config import db_manager, USE_SUPABASE
from database.models_tenant import (
    Product, Category, 
    StockMovement as StockMovementModel, StockMovementType,
    InventorySession as InventorySessionModel,
    InventoryItem as InventoryItemModel
)
from database.repositories import ProductRepository, CategoryRepository
from sqlalchemy import desc, func

def get_session():
    if USE_SUPABASE:
        return db_manager.get_tenant_session("default")
    return db_manager.get_tenant_session("pharmacie_centrale")


def session_to_dict(session: InventorySessionModel, include_items: bool = True) -> dict:
    """Convertir une session en dictionnaire"""
    result = {
        "id": str(session.id),
        "name": session.name,
        "status": session.status,
        "stats": {
            "total_items": session.total_items,
            "counted_items": session.counted_items,
            "items_with_discrepancy": session.items_with_discrepancy,
            "total_discrepancy_value": session.total_discrepancy_value or 0
        },
        "total_positive_discrepancy": session.total_positive_discrepancy or 0,
        "total_negative_discrepancy": session.total_negative_discrepancy or 0,
        "products_with_discrepancy": session.items_with_discrepancy or 0,
        "validated_at": session.validated_at.isoformat() if session.validated_at else None,
        "validated_by": session.validated_by,
        "validation_notes": session.validation_notes,
        "adjustments_applied": session.adjustments_applied,
        "created_by": session.created_by,
        "created_at": session.created_at.isoformat() if session.created_at else None
    }
    
    if include_items and session.items:
        result["items"] = [item_to_dict(item) for item in session.items]
    
    return result


def item_to_dict(item: InventoryItemModel) -> dict:
    """Convertir un item en dictionnaire"""
    return {
        "id": str(item.id),
        "product_id": str(item.product_id),
        "product_name": item.product_name,
        "product_code": item.product_code,
        "category_name": item.category_name,
        "theoretical_quantity": item.theoretical_quantity,
        "original_theoretical_quantity": item.original_theoretical_quantity,
        "actual_quantity": item.actual_quantity,
        "discrepancy": item.discrepancy,
        "unit_cost": item.unit_cost,
        "discrepancy_value": item.discrepancy_value,
        "notes": item.notes,
        "theoretical_movement_note": item.theoretical_movement_note,
        "counted_at": item.counted_at.isoformat() if item.counted_at else None
    }


def update_theoretical_quantities(db_session, session: InventorySessionModel):
    """Met à jour les quantités théoriques avec le stock actuel"""
    if session.status != 'in_progress':
        return
    
    product_repo = ProductRepository()
    auto_updated_count = 0
    
    for item in session.items:
        product = product_repo.get_by_id_str(str(item.product_id))
        if not product:
            continue
        
        current_stock = product.get('stock', 0) or 0
        original = item.original_theoretical_quantity or item.theoretical_quantity
        
        if current_stock != original:
            diff = current_stock - original
            movement_type = "entrées" if diff > 0 else "sorties"
            
            item.theoretical_quantity = current_stock
            item.theoretical_movement_note = f"Stock modifié: {abs(diff)} {movement_type}"
            auto_updated_count += 1
            
            if item.actual_quantity is not None:
                item.discrepancy = item.actual_quantity - current_stock
                item.discrepancy_value = round(item.discrepancy * (item.unit_cost or 0), 2)
    
    if auto_updated_count > 0:
        db_session.commit()


def recalculate_session_stats(db_session, session: InventorySessionModel):
    """Recalculer les statistiques de la session"""
    counted = 0
    with_discrepancy = 0
    positive_disc = 0
    negative_disc = 0
    total_value = 0
    
    for item in session.items:
        if item.actual_quantity is not None:
            counted += 1
            if item.discrepancy and item.discrepancy != 0:
                with_discrepancy += 1
                if item.discrepancy > 0:
                    positive_disc += item.discrepancy
                else:
                    negative_disc += abs(item.discrepancy)
                total_value += item.discrepancy_value or 0
    
    session.counted_items = counted
    session.items_with_discrepancy = with_discrepancy
    session.total_positive_discrepancy = positive_disc
    session.total_negative_discrepancy = negative_disc
    session.total_discrepancy_value = total_value
    
    db_session.commit()


@router.get("/movements")
async def get_stock_movements(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    product_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer les mouvements de stock"""
    with get_session() as db_session:
        query = db_session.query(StockMovementModel).order_by(desc(StockMovementModel.created_at))
        
        if product_id:
            try:
                query = query.filter(StockMovementModel.product_id == uuid.UUID(product_id))
            except ValueError:
                pass
        
        total = query.count()
        movements = query.offset(skip).limit(limit).all()
        
        return {
            "items": [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "movement_type": m.movement_type.value if m.movement_type else None,
                    "quantity": m.quantity,
                    "stock_after": m.stock_after,
                    "reference_type": m.reference_type,
                    "reference_id": str(m.reference_id) if m.reference_id else None,
                    "reason": m.reason,
                    "agent_code": m.agent_code,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in movements
            ],
            "total": total,
            "limit": limit,
            "skip": skip
        }


@router.get("/sessions/active")
async def get_active_session(
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Récupérer la session d'inventaire active"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.status == 'in_progress'
        ).first()
        
        if not session:
            return None
        
        update_theoretical_quantities(db_session, session)
        return session_to_dict(session)


@router.get("/sessions/history")
async def get_inventory_history(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    year: Optional[int] = Query(None, description="Filtrer par année"),
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Récupérer l'historique des sessions d'inventaire avec pagination et filtre par année"""
    with get_session() as db_session:
        query = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.status.in_(['completed', 'cancelled'])
        )
        
        # Filtre par année
        if year:
            query = query.filter(
                func.extract('year', InventorySessionModel.created_at) == year
            )
        
        # Compter le total
        total = query.count()
        
        # Appliquer pagination et tri
        sessions = query.order_by(desc(InventorySessionModel.created_at)).offset(skip).limit(limit).all()
        
        # Récupérer les années disponibles pour le filtre
        years_query = db_session.query(
            func.distinct(func.extract('year', InventorySessionModel.created_at))
        ).filter(
            InventorySessionModel.status.in_(['completed', 'cancelled'])
        ).all()
        available_years = sorted([int(y[0]) for y in years_query if y[0]], reverse=True)
        
        return {
            "items": [session_to_dict(s, include_items=True) for s in sessions],
            "total": total,
            "limit": limit,
            "skip": skip,
            "has_more": skip + len(sessions) < total,
            "available_years": available_years
        }


@router.post("/sessions")
async def create_inventory_session(
    session_data: InventorySessionCreate,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Créer une nouvelle session d'inventaire"""
    with get_session() as db_session:
        # Vérifier s'il existe déjà une session active
        existing = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.status == 'in_progress'
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Une session d'inventaire est déjà en cours"
            )
        
        product_repo = ProductRepository()
        category_repo = CategoryRepository()
        
        # Récupérer les produits à inventorier
        products = product_repo.get_all()
        
        # Filtrer par catégorie si spécifié
        if session_data.category_id:
            products = [p for p in products if p.get('category_id') == session_data.category_id]
        
        if not products:
            raise HTTPException(status_code=400, detail="Aucun produit à inventorier")
        
        # Créer la session
        session_id = uuid.uuid4()
        inventory_session = InventorySessionModel(
            id=session_id,
            name=session_data.name or f"Inventaire du {datetime.now().strftime('%d/%m/%Y')}",
            status='in_progress',
            total_items=len(products),
            counted_items=0,
            items_with_discrepancy=0,
            created_by=current_user.get('employee_code', 'N/A')
        )
        db_session.add(inventory_session)
        
        # Créer les items
        for product in products:
            category = category_repo.get_by_id(product.get('category_id')) if product.get('category_id') else None
            unit_cost = product.get('purchase_price') or product.get('unit_price') or 0
            stock = product.get('stock', 0) or 0
            
            item = InventoryItemModel(
                id=uuid.uuid4(),
                session_id=session_id,
                product_id=uuid.UUID(product['id']),
                product_name=product.get('name'),
                product_code=product.get('internal_reference'),
                category_name=category.get('name') if category else None,
                theoretical_quantity=stock,
                original_theoretical_quantity=stock,
                unit_cost=unit_cost
            )
            db_session.add(item)
        
        db_session.commit()
        db_session.refresh(inventory_session)
        
        return session_to_dict(inventory_session)


@router.get("/sessions/{session_id}")
async def get_inventory_session(
    session_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Récupérer une session d'inventaire par ID"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.id == uuid.UUID(session_id)
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        if session.status == 'in_progress':
            update_theoretical_quantities(db_session, session)
        
        return session_to_dict(session)


@router.put("/sessions/{session_id}/items/{item_id}")
async def update_inventory_item(
    session_id: str,
    item_id: str,
    item_update: InventoryItemUpdate,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Mettre à jour un item d'inventaire (comptage)"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.id == uuid.UUID(session_id)
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        if session.status != 'in_progress':
            raise HTTPException(status_code=400, detail="Cette session n'est plus modifiable")
        
        item = db_session.query(InventoryItemModel).filter(
            InventoryItemModel.id == uuid.UUID(item_id),
            InventoryItemModel.session_id == uuid.UUID(session_id)
        ).first()
        
        if not item:
            raise HTTPException(status_code=404, detail="Item non trouvé")
        
        # Mettre à jour le comptage
        if item_update.actual_quantity is not None:
            item.actual_quantity = item_update.actual_quantity
            item.discrepancy = item_update.actual_quantity - item.theoretical_quantity
            item.discrepancy_value = round(item.discrepancy * (item.unit_cost or 0), 2)
            item.counted_at = datetime.now(timezone.utc)
        
        if item_update.note is not None:
            item.notes = item_update.note
        
        db_session.commit()
        
        # Recalculer les stats
        recalculate_session_stats(db_session, session)
        
        return item_to_dict(item)


@router.post("/sessions/{session_id}/validate")
async def validate_inventory_session(
    session_id: str,
    validation: InventoryValidation,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Valider et clôturer une session d'inventaire"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.id == uuid.UUID(session_id)
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        if session.status != 'in_progress':
            raise HTTPException(status_code=400, detail="Cette session n'est plus modifiable")
        
        product_repo = ProductRepository()
        adjustments = []
        
        if validation.apply_adjustments:
            for item in session.items:
                if item.actual_quantity is not None and item.discrepancy != 0:
                    new_stock = item.actual_quantity
                    
                    # Mettre à jour le stock
                    product_repo.update_by_id_str(
                        str(item.product_id),
                        {'stock': new_stock}
                    )
                    
                    # Créer mouvement de stock
                    adjustment_type = "Excédent" if item.discrepancy > 0 else "Manque"
                    justification = item.notes or 'Non spécifié'
                    
                    movement = StockMovementModel(
                        id=uuid.uuid4(),
                        product_id=item.product_id,
                        movement_type=StockMovementType.ADJUSTMENT,
                        quantity=item.discrepancy,
                        stock_after=new_stock,
                        reference_type="inventory",
                        reference_id=uuid.UUID(session_id),
                        agent_code=current_user.get('employee_code', 'N/A'),
                        reason=f"[{adjustment_type}] {justification} | Théorique: {item.theoretical_quantity} → Réel: {new_stock}"
                    )
                    db_session.add(movement)
                    
                    adjustments.append({
                        "product_id": str(item.product_id),
                        "product_name": item.product_name,
                        "old_stock": item.theoretical_quantity,
                        "new_stock": new_stock,
                        "adjustment": item.discrepancy,
                        "justification": justification
                    })
        
        # Mettre à jour la session
        session.status = 'completed'
        session.validated_at = datetime.now(timezone.utc)
        session.validated_by = current_user.get('employee_code', 'N/A')
        session.validation_notes = validation.validation_notes
        session.adjustments_applied = validation.apply_adjustments
        
        db_session.commit()
        
        return {
            "message": "Session d'inventaire validée",
            "session_id": session_id,
            "adjustments_count": len(adjustments),
            "adjustments": adjustments
        }


@router.delete("/sessions/{session_id}")
async def cancel_inventory_session(
    session_id: str,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Annuler une session d'inventaire"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.id == uuid.UUID(session_id)
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        if session.status != 'in_progress':
            raise HTTPException(status_code=400, detail="Seules les sessions en cours peuvent être annulées")
        
        session.status = 'cancelled'
        db_session.commit()
        
        return {"message": "Session annulée", "session_id": session_id}


@router.post("/sessions/{session_id}/refresh-theoretical")
async def refresh_theoretical_stock(
    session_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Recalculer tous les stocks théoriques depuis le stock actuel"""
    with get_session() as db_session:
        session = db_session.query(InventorySessionModel).filter(
            InventorySessionModel.id == uuid.UUID(session_id)
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session non trouvée")
        
        if session.status != 'in_progress':
            raise HTTPException(status_code=400, detail="Cette session n'est plus modifiable")
        
        product_repo = ProductRepository()
        updated_count = 0
        
        for item in session.items:
            product = product_repo.get_by_id_str(str(item.product_id))
            if product:
                current_stock = product.get('stock', 0) or 0
                item.theoretical_quantity = current_stock
                item.original_theoretical_quantity = current_stock
                item.theoretical_movement_note = None
                
                if item.actual_quantity is not None:
                    item.discrepancy = item.actual_quantity - current_stock
                    item.discrepancy_value = round(item.discrepancy * (item.unit_cost or 0), 2)
                
                updated_count += 1
        
        db_session.commit()
        recalculate_session_stats(db_session, session)
        
        return {
            "message": f"{updated_count} stocks théoriques recalculés",
            "session_id": session_id
        }
