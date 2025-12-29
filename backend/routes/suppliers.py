from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role
from models.supplier import Supplier, SupplierCreate

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

@router.post("", response_model=Supplier)
async def create_supplier(supplier_data: SupplierCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a new supplier"""
    supplier_dict = supplier_data.model_dump()
    supplier_dict['tenant_id'] = current_user['tenant_id']
    supplier_obj = Supplier(**supplier_dict)
    
    doc = supplier_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.suppliers.insert_one(doc)
    return supplier_obj

@router.get("", response_model=List[Supplier])
async def get_suppliers(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get all suppliers"""
    suppliers = await db.suppliers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for supplier in suppliers:
        if isinstance(supplier['created_at'], str):
            supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
    return suppliers

@router.get("/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get a specific supplier"""
    supplier = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if isinstance(supplier['created_at'], str):
        supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
    return Supplier(**supplier)

@router.put("/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: str, supplier_data: SupplierCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Update a supplier"""
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_data.model_dump()
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    
    updated_supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if isinstance(updated_supplier['created_at'], str):
        updated_supplier['created_at'] = datetime.fromisoformat(updated_supplier['created_at'])
    return Supplier(**updated_supplier)

@router.delete("/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Delete a supplier"""
    # Vérifier si le fournisseur a déjà livré au moins une fois
    deliveries_count = await db.stock_movements.count_documents({
        "tenant_id": current_user['tenant_id'],
        "supplier_id": supplier_id,
        "type": "in"
    })
    if deliveries_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer ce fournisseur : il a effectué {deliveries_count} livraison(s). Vous pouvez le désactiver en modifiant ses informations."
        )
    
    result = await db.suppliers.delete_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}
