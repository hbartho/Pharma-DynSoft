from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone
from database import db
from auth import get_current_user
from models.sync import SyncData

router = APIRouter(prefix="/sync", tags=["Synchronization"])

@router.post("/push")
async def sync_push(sync_data: SyncData, current_user: dict = Depends(get_current_user)):
    """Push changes to server"""
    for change in sync_data.changes:
        change['tenant_id'] = current_user['tenant_id']
        change['user_id'] = current_user['user_id']
        change['synced'] = True
        change['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        if change['type'] == 'product':
            if change['action'] == 'create':
                await db.products.insert_one(change['payload'])
            elif change['action'] == 'update':
                await db.products.update_one({"id": change['payload']['id']}, {"$set": change['payload']})
            elif change['action'] == 'delete':
                await db.products.delete_one({"id": change['payload']['id']})
        
        elif change['type'] == 'sale':
            if change['action'] == 'create':
                await db.sales.insert_one(change['payload'])
        
        await db.sync_logs.insert_one(change)
    
    return {"message": f"Synced {len(sync_data.changes)} changes"}

@router.get("/pull")
async def sync_pull(since: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    """Pull changes from server"""
    query = {"tenant_id": current_user['tenant_id']}
    if since:
        query['updated_at'] = {"$gt": since}
    
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    sales = await db.sales.find(query, {"_id": 0}).to_list(1000)
    customers = await db.customers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    return {
        "products": products,
        "sales": sales,
        "customers": customers
    }
