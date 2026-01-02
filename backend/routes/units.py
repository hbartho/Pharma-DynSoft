from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role, get_current_user
from models.unit import Unit, UnitCreate

router = APIRouter(prefix="/units", tags=["Units"])

@router.post("", response_model=Unit)
async def create_unit(unit_data: UnitCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a new product unit"""
    # Vérifier si une unité avec le même nom existe
    existing = await db.units.find_one({
        "tenant_id": current_user['tenant_id'],
        "name": {"$regex": f"^{unit_data.name}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"Une unité avec le nom '{unit_data.name}' existe déjà")
    
    unit_dict = unit_data.model_dump()
    unit_dict['tenant_id'] = current_user['tenant_id']
    unit_obj = Unit(**unit_dict)
    
    doc = unit_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.units.insert_one(doc)
    return unit_obj

@router.get("", response_model=List[Unit])
async def get_units(current_user: dict = Depends(get_current_user)):
    """Get all product units"""
    units = await db.units.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for unit in units:
        if isinstance(unit.get('created_at'), str):
            unit['created_at'] = datetime.fromisoformat(unit['created_at'])
    return units

@router.get("/{unit_id}", response_model=Unit)
async def get_unit(unit_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific unit"""
    unit = await db.units.find_one({"id": unit_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    if isinstance(unit.get('created_at'), str):
        unit['created_at'] = datetime.fromisoformat(unit['created_at'])
    return Unit(**unit)

@router.put("/{unit_id}", response_model=Unit)
async def update_unit(unit_id: str, unit_data: UnitCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Update a unit"""
    existing = await db.units.find_one({"id": unit_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Vérifier si une autre unité avec le même nom existe
    existing_name = await db.units.find_one({
        "tenant_id": current_user['tenant_id'],
        "name": {"$regex": f"^{unit_data.name}$", "$options": "i"},
        "id": {"$ne": unit_id}
    })
    if existing_name:
        raise HTTPException(status_code=400, detail=f"Une autre unité avec le nom '{unit_data.name}' existe déjà")
    
    update_data = unit_data.model_dump()
    await db.units.update_one({"id": unit_id}, {"$set": update_data})
    
    updated_unit = await db.units.find_one({"id": unit_id}, {"_id": 0})
    if isinstance(updated_unit.get('created_at'), str):
        updated_unit['created_at'] = datetime.fromisoformat(updated_unit['created_at'])
    return Unit(**updated_unit)

@router.delete("/{unit_id}")
async def delete_unit(unit_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Delete a unit"""
    # Vérifier si l'unité est utilisée par des produits
    products_using = await db.products.count_documents({"unit_id": unit_id, "tenant_id": current_user['tenant_id']})
    if products_using > 0:
        raise HTTPException(status_code=400, detail=f"Impossible de supprimer: {products_using} produit(s) utilisent cette unité")
    
    result = await db.units.delete_one({"id": unit_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Unit not found")
    return {"message": "Unit deleted successfully"}
