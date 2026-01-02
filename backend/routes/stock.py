from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.stock import StockMovement, StockMovementCreate, StockMovementType, StockSummary
import uuid

router = APIRouter(prefix="/stock", tags=["Stock"])


async def get_user_name(user_id: str, tenant_id: str) -> str:
    if not user_id:
        return None
    user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
    if user:
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        return f"{first} {last}".strip() or user.get("name", "Utilisateur")
    return "Utilisateur inconnu"


async def get_product_info(product_id: str, tenant_id: str) -> dict:
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if product:
        return {"name": product.get("name"), "stock": product.get("stock", 0)}
    return {"name": "Produit inconnu", "stock": 0}


async def create_stock_movement(
    product_id: str,
    movement_type: StockMovementType,
    movement_quantity: int,
    tenant_id: str,
    user_id: str,
    reference_type: str = None,
    reference_id: str = None,
    notes: str = None
) -> StockMovement:
    """Créer un mouvement de stock et mettre à jour le produit"""
    # Récupérer le produit
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    stock_before = product.get("stock", 0)
    stock_after = stock_before + movement_quantity
    
    # Vérifier que le stock ne devient pas négatif (sauf ajustement)
    if stock_after < 0 and movement_type != StockMovementType.ADJUSTMENT:
        raise HTTPException(status_code=400, detail=f"Stock insuffisant. Stock actuel: {stock_before}")
    
    # Créer le mouvement
    movement = StockMovement(
        product_id=product_id,
        product_name=product.get("name"),
        movement_type=movement_type,
        movement_quantity=movement_quantity,
        stock_before=stock_before,
        stock_after=max(0, stock_after),
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        tenant_id=tenant_id,
        created_by=user_id
    )
    
    doc = movement.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["movement_type"] = doc["movement_type"].value
    
    await db.stock_movements.insert_one(doc)
    
    # Mettre à jour le stock du produit
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"stock": max(0, stock_after), "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return movement


@router.get("/movements", response_model=List[StockMovement])
async def get_stock_movements(
    product_id: Optional[str] = None,
    movement_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer l'historique des mouvements de stock"""
    tenant_id = current_user["tenant_id"]
    
    query = {"tenant_id": tenant_id}
    if product_id:
        query["product_id"] = product_id
    if movement_type:
        query["movement_type"] = movement_type
    
    movements = await db.stock_movements.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    # Enrichir avec les noms
    for mov in movements:
        mov["created_by_name"] = await get_user_name(mov.get("created_by"), tenant_id)
        if isinstance(mov.get("created_at"), str):
            mov["created_at"] = datetime.fromisoformat(mov["created_at"])
    
    return [StockMovement(**mov) for mov in movements]


@router.get("/movements/{product_id}", response_model=List[StockMovement])
async def get_product_stock_history(
    product_id: str,
    limit: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer l'historique de stock d'un produit spécifique"""
    tenant_id = current_user["tenant_id"]
    
    movements = await db.stock_movements.find(
        {"product_id": product_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    for mov in movements:
        mov["created_by_name"] = await get_user_name(mov.get("created_by"), tenant_id)
        if isinstance(mov.get("created_at"), str):
            mov["created_at"] = datetime.fromisoformat(mov["created_at"])
    
    return [StockMovement(**mov) for mov in movements]


@router.post("/adjustment", response_model=StockMovement)
async def create_stock_adjustment(
    data: StockMovementCreate,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Créer un ajustement de stock manuel"""
    tenant_id = current_user["tenant_id"]
    
    movement = await create_stock_movement(
        product_id=data.product_id,
        movement_type=StockMovementType.ADJUSTMENT,
        movement_quantity=data.movement_quantity,
        tenant_id=tenant_id,
        user_id=current_user["id"],
        reference_type="adjustment",
        notes=data.notes
    )
    
    return movement


@router.get("/summary/{product_id}", response_model=StockSummary)
async def get_stock_summary(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer le résumé de stock d'un produit"""
    tenant_id = current_user["tenant_id"]
    
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Calculer les totaux
    movements = await db.stock_movements.find(
        {"product_id": product_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).to_list(10000)
    
    total_entries = sum(m.get("movement_quantity", 0) for m in movements if m.get("movement_quantity", 0) > 0)
    total_exits = abs(sum(m.get("movement_quantity", 0) for m in movements if m.get("movement_quantity", 0) < 0))
    
    last_movement = await db.stock_movements.find_one(
        {"product_id": product_id, "tenant_id": tenant_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    last_date = None
    if last_movement and last_movement.get("created_at"):
        last_date = datetime.fromisoformat(last_movement["created_at"]) if isinstance(last_movement["created_at"], str) else last_movement["created_at"]
    
    return StockSummary(
        product_id=product_id,
        product_name=product.get("name", "Inconnu"),
        current_stock=product.get("stock", 0),
        total_entries=total_entries,
        total_exits=total_exits,
        last_movement_date=last_date,
        movements_count=len(movements)
    )
