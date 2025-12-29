from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role, get_current_user
from models.sale import Sale, SaleCreate

router = APIRouter(prefix="/sales", tags=["Sales"])

@router.post("", response_model=Sale)
async def create_sale(sale_data: SaleCreate, current_user: dict = Depends(get_current_user)):
    """Create a new sale"""
    sale_dict = sale_data.model_dump()
    sale_dict['tenant_id'] = current_user['tenant_id']
    sale_dict['user_id'] = current_user['user_id']
    sale_obj = Sale(**sale_dict)
    
    for item in sale_data.items:
        product = await db.products.find_one({"id": item['product_id'], "tenant_id": current_user['tenant_id']})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
        
        new_stock = product['stock'] - item['quantity']
        if new_stock < 0:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product['name']}")
        
        await db.products.update_one({"id": item['product_id']}, {"$set": {"stock": new_stock}})
    
    doc = sale_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sales.insert_one(doc)
    return sale_obj

@router.get("")
async def get_sales(current_user: dict = Depends(get_current_user)):
    """Get all sales with user information"""
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Récupérer tous les utilisateurs pour enrichir les ventes
    users = await db.users.find({"tenant_id": current_user['tenant_id']}, {"_id": 0, "password": 0}).to_list(1000)
    users_map = {u['id']: u for u in users}
    
    for sale in sales:
        if isinstance(sale['created_at'], str):
            sale['created_at'] = datetime.fromisoformat(sale['created_at'])
        # Ajouter le nom de l'agent
        if sale.get('user_id') and sale['user_id'] in users_map:
            sale['user_name'] = users_map[sale['user_id']]['name']
        else:
            sale['user_name'] = 'Inconnu'
    return sales

@router.get("/{sale_id}", response_model=Sale)
async def get_sale(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific sale"""
    sale = await db.sales.find_one({"id": sale_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    if isinstance(sale['created_at'], str):
        sale['created_at'] = datetime.fromisoformat(sale['created_at'])
    return Sale(**sale)

@router.delete("/{sale_id}")
async def delete_sale(sale_id: str, current_user: dict = Depends(require_role(["admin"]))):
    """
    Suppression de vente désactivée pour des raisons d'historique et de prévention de fraude.
    Les ventes ne peuvent pas être supprimées une fois enregistrées.
    """
    raise HTTPException(
        status_code=403, 
        detail="La suppression des ventes est désactivée pour des raisons d'historique et de prévention de fraude. Les ventes enregistrées ne peuvent pas être supprimées."
    )
