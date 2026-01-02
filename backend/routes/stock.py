from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.stock import StockMovement, StockMovementCreate, StockMovementType, StockSummary
import uuid

router = APIRouter(prefix="/stock", tags=["Stock"])


async def get_valuation_for_product(product_id: str, tenant_id: str, method: str = "weighted_average") -> dict:
    """Calculer la valorisation du stock pour un produit"""
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if not product:
        return {"unit_cost": 0, "total_value": 0}
    
    current_stock = product.get("stock", 0)
    purchase_price = product.get("purchase_price", 0)
    
    if current_stock <= 0:
        return {"unit_cost": 0, "total_value": 0}
    
    # Méthode simple basée sur le prix d'achat
    if method == "fifo" or method == "weighted_average":
        unit_cost = purchase_price
        total_value = current_stock * unit_cost
    else:
        unit_cost = purchase_price
        total_value = current_stock * unit_cost
    
    return {"unit_cost": unit_cost, "total_value": total_value}


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
    employee_code: str,
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
    
    # Créer le mouvement avec employee_code
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
        created_by=employee_code  # Utiliser employee_code
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
    
    # Convertir les dates
    for mov in movements:
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
    employee_code = current_user.get("employee_code", "N/A")
    
    movement = await create_stock_movement(
        product_id=data.product_id,
        movement_type=StockMovementType.ADJUSTMENT,
        movement_quantity=data.movement_quantity,
        tenant_id=tenant_id,
        employee_code=employee_code,
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


@router.get("/alerts")
async def get_stock_alerts(
    threshold: int = Query(default=10, description="Seuil de stock bas"),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer les alertes de stock bas"""
    tenant_id = current_user["tenant_id"]
    
    low_stock_products = await db.products.find(
        {"tenant_id": tenant_id, "stock": {"$lte": threshold}},
        {"_id": 0, "password": 0}
    ).to_list(1000)
    
    return low_stock_products


@router.get("/valuation")
async def get_stock_valuation(
    method: str = Query(default="weighted_average", description="Méthode: fifo, lifo, weighted_average"),
    current_user: dict = Depends(get_current_user)
):
    """Calculer la valorisation totale du stock"""
    tenant_id = current_user["tenant_id"]
    
    products = await db.products.find(
        {"tenant_id": tenant_id, "stock": {"$gt": 0}},
        {"_id": 0}
    ).to_list(10000)
    
    total_valuation = 0
    valuations = []
    
    for product in products:
        valuation = await get_valuation_for_product(product["id"], tenant_id, method)
        total_valuation += valuation["total_value"]
        valuations.append({
            "product_id": product["id"],
            "product_name": product.get("name"),
            "stock": product.get("stock", 0),
            "unit_cost": valuation["unit_cost"],
            "total_value": valuation["total_value"]
        })
    
    return {
        "method": method,
        "total_valuation": total_valuation,
        "products": valuations
    }
