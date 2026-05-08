"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from auth import require_role, get_current_user
from models.unit import Unit, UnitCreate, UnitUpdate
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/units", tags=["Units"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import UnitRepository, ProductRepository
    
    @router.post("", response_model=Unit)
    async def create_unit(unit_data: UnitCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Create a new product unit"""
        repo = UnitRepository()
        
        # Check if unit with same name exists
        existing = repo.get_by_name(unit_data.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Une unité avec le nom '{unit_data.name}' existe déjà")
        
        data = unit_data.model_dump()
        result = repo.create(data)
        return Unit(**result)
    
    @router.get("", response_model=List[Unit])
    async def get_units(current_user: dict = Depends(get_current_user)):
        """Get all product units"""
        repo = UnitRepository()
        units = repo.get_all()
        return [Unit(**u) for u in units]
    
    @router.get("/{unit_id}", response_model=Unit)
    async def get_unit(unit_id: str, current_user: dict = Depends(get_current_user)):
        """Get a specific unit"""
        repo = UnitRepository()
        unit = repo.get_by_id_str(unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")
        return Unit(**unit)
    
    @router.put("/{unit_id}", response_model=Unit)
    async def update_unit(unit_id: str, unit_data: UnitUpdate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Update a unit"""
        repo = UnitRepository()
        
        # Check if unit exists
        existing = repo.get_by_id_str(unit_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Unit not found")
        
        # Check if another unit with same name exists
        if unit_data.name:
            existing_name = repo.get_by_name(unit_data.name)
            if existing_name and existing_name['id'] != unit_id:
                raise HTTPException(status_code=400, detail=f"Une autre unité avec le nom '{unit_data.name}' existe déjà")
        
        update_data = {k: v for k, v in unit_data.model_dump().items() if v is not None}
        result = repo.update_by_id_str(unit_id, update_data)
        return Unit(**result)
    
    @router.delete("/{unit_id}")
    async def delete_unit(unit_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Delete a unit"""
        product_repo = ProductRepository()
        
        # Check if unit is used by products
        products = product_repo.get_by_unit(unit_id)
        if len(products) > 0:
            raise HTTPException(status_code=400, detail=f"Impossible de supprimer: {len(products)} produit(s) utilisent cette unité")
        
        repo = UnitRepository()
        success = repo.delete_by_id_str(unit_id)
        if not success:
            raise HTTPException(status_code=404, detail="Unit not found")
        return {"message": "Unit deleted successfully"}
