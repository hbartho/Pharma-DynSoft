from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role, get_current_user
from models.stock import StockMovement, StockMovementCreate

router = APIRouter(prefix="/stock", tags=["Stock"])

# Stock Valuation Functions
async def calculate_fifo_value(product_id: str, tenant_id: str) -> dict:
    """Calcul FIFO: les premiers entrés sont les premiers sortis"""
    movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "in"
    }, {"_id": 0}).sort("created_at", 1).to_list(1000)
    
    out_movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "out"
    }, {"_id": 0}).to_list(1000)
    total_out = sum(m.get('quantity', 0) for m in out_movements)
    
    remaining_out = total_out
    total_value = 0
    total_qty = 0
    
    for m in movements:
        qty = m.get('quantity', 0)
        price = m.get('unit_price', 0)
        
        if remaining_out >= qty:
            remaining_out -= qty
        else:
            available = qty - remaining_out
            remaining_out = 0
            total_value += available * price
            total_qty += available
    
    return {
        "total_quantity": total_qty,
        "total_value": round(total_value, 2),
        "unit_cost": round(total_value / total_qty, 2) if total_qty > 0 else 0
    }

async def calculate_lifo_value(product_id: str, tenant_id: str) -> dict:
    """Calcul LIFO: les derniers entrés sont les premiers sortis"""
    movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "in"
    }, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    out_movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "out"
    }, {"_id": 0}).to_list(1000)
    total_out = sum(m.get('quantity', 0) for m in out_movements)
    
    remaining_out = total_out
    total_value = 0
    total_qty = 0
    
    for m in movements:
        qty = m.get('quantity', 0)
        price = m.get('unit_price', 0)
        
        if remaining_out >= qty:
            remaining_out -= qty
        else:
            available = qty - remaining_out
            remaining_out = 0
            total_value += available * price
            total_qty += available
    
    return {
        "total_quantity": total_qty,
        "total_value": round(total_value, 2),
        "unit_cost": round(total_value / total_qty, 2) if total_qty > 0 else 0
    }

async def calculate_weighted_average_value(product_id: str, tenant_id: str) -> dict:
    """Calcul Moyenne Pondérée: coût moyen de toutes les entrées"""
    movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "in"
    }, {"_id": 0}).to_list(1000)
    
    total_cost = sum(m.get('quantity', 0) * m.get('unit_price', 0) for m in movements)
    total_in_qty = sum(m.get('quantity', 0) for m in movements)
    
    out_movements = await db.stock_movements.find({
        "tenant_id": tenant_id,
        "product_id": product_id,
        "type": "out"
    }, {"_id": 0}).to_list(1000)
    total_out = sum(m.get('quantity', 0) for m in out_movements)
    
    current_qty = total_in_qty - total_out
    avg_cost = total_cost / total_in_qty if total_in_qty > 0 else 0
    
    return {
        "total_quantity": current_qty,
        "total_value": round(current_qty * avg_cost, 2),
        "unit_cost": round(avg_cost, 2)
    }

async def get_valuation_for_product(product_id: str, tenant_id: str, method: str) -> dict:
    """Get valuation for a product based on method"""
    if method == 'fifo':
        return await calculate_fifo_value(product_id, tenant_id)
    elif method == 'lifo':
        return await calculate_lifo_value(product_id, tenant_id)
    else:
        return await calculate_weighted_average_value(product_id, tenant_id)

@router.post("", response_model=StockMovement)
async def create_stock_movement(movement_data: StockMovementCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a stock movement"""
    movement_dict = movement_data.model_dump()
    movement_dict['tenant_id'] = current_user['tenant_id']
    movement_obj = StockMovement(**movement_dict)
    
    product = await db.products.find_one({"id": movement_data.product_id, "tenant_id": current_user['tenant_id']})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if movement_data.type == "in":
        new_stock = product['stock'] + movement_data.quantity
    else:
        new_stock = product['stock'] - movement_data.quantity
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")
    
    await db.products.update_one({"id": movement_data.product_id}, {"$set": {"stock": new_stock}})
    
    doc = movement_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.stock_movements.insert_one(doc)
    return movement_obj

@router.get("", response_model=List[StockMovement])
async def get_stock_movements(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get all stock movements"""
    movements = await db.stock_movements.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for movement in movements:
        if isinstance(movement['created_at'], str):
            movement['created_at'] = datetime.fromisoformat(movement['created_at'])
    return movements

@router.get("/alerts")
async def get_stock_alerts(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get products with low stock"""
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    alerts = [p for p in products if p['stock'] <= p['min_stock']]
    return alerts

@router.get("/valuation/{product_id}")
async def get_product_stock_valuation(product_id: str, current_user: dict = Depends(get_current_user)):
    """Get stock valuation for a specific product"""
    settings = await db.settings.find_one({"tenant_id": current_user['tenant_id']}, {"_id": 0})
    method = settings.get('stock_valuation_method', 'weighted_average') if settings else 'weighted_average'
    
    valuation = await get_valuation_for_product(product_id, current_user['tenant_id'], method)
    valuation['method'] = method
    return valuation

@router.get("/valuation")
async def get_total_stock_valuation(current_user: dict = Depends(get_current_user)):
    """Get total stock valuation"""
    settings = await db.settings.find_one({"tenant_id": current_user['tenant_id']}, {"_id": 0})
    method = settings.get('stock_valuation_method', 'weighted_average') if settings else 'weighted_average'
    
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    total_value = 0
    products_valuation = []
    
    for product in products:
        valuation = await get_valuation_for_product(product['id'], current_user['tenant_id'], method)
        
        # Si pas de mouvements, utiliser le prix de vente comme estimation
        if valuation['total_value'] == 0 and product.get('stock', 0) > 0:
            estimated_cost = product.get('price', 0) * 0.7
            valuation['total_value'] = round(product['stock'] * estimated_cost, 2)
            valuation['unit_cost'] = round(estimated_cost, 2)
            valuation['total_quantity'] = product['stock']
            valuation['estimated'] = True
        
        total_value += valuation['total_value']
        products_valuation.append({
            "product_id": product['id'],
            "product_name": product['name'],
            "stock": product.get('stock', 0),
            **valuation
        })
    
    return {
        "method": method,
        "total_value": round(total_value, 2),
        "products_count": len(products),
        "currency": settings.get('currency', 'EUR') if settings else 'EUR',
        "products": products_valuation
    }
