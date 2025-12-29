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

@router.get("", response_model=List[Sale])
async def get_sales(current_user: dict = Depends(get_current_user)):
    """Get all sales"""
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for sale in sales:
        if isinstance(sale['created_at'], str):
            sale['created_at'] = datetime.fromisoformat(sale['created_at'])
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
    """Delete a sale (Admin only) - restores stock"""
    sale = await db.sales.find_one({"id": sale_id, "tenant_id": current_user['tenant_id']})
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    
    # Restore stock for each item
    for item in sale.get('items', []):
        product = await db.products.find_one({"id": item['product_id'], "tenant_id": current_user['tenant_id']})
        if product:
            new_stock = product['stock'] + item['quantity']
            await db.products.update_one({"id": item['product_id']}, {"$set": {"stock": new_stock}})
    
    result = await db.sales.delete_one({"id": sale_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sale not found")
    return {"message": "Sale deleted and stock restored successfully"}
