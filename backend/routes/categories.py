"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
from auth import require_role, get_current_user
from models.category import Category, CategoryCreate, CategoryUpdate
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/categories", tags=["Categories"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import CategoryRepository
    
    @router.post("", response_model=Category)
    async def create_category(category_data: CategoryCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Create a new category"""
        repo = CategoryRepository()
        data = category_data.model_dump()
        result = repo.create(data)
        return Category(**result)
    
    @router.get("", response_model=List[Category])
    async def get_categories(current_user: dict = Depends(get_current_user)):
        """Get all categories"""
        repo = CategoryRepository()
        categories = repo.get_all()
        return [Category(**c) for c in categories]
    
    @router.get("/{category_id}", response_model=Category)
    async def get_category(category_id: str, current_user: dict = Depends(get_current_user)):
        """Get a specific category"""
        repo = CategoryRepository()
        category = repo.get_by_id_str(category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return Category(**category)
    
    @router.put("/{category_id}", response_model=Category)
    async def update_category(category_id: str, category_data: CategoryUpdate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Update a category"""
        repo = CategoryRepository()
        update_data = {k: v for k, v in category_data.model_dump().items() if v is not None}
        result = repo.update_by_id_str(category_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Category not found")
        return Category(**result)
    
    @router.delete("/{category_id}")
    async def delete_category(category_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Delete a category"""
        from database.repositories import ProductRepository
        product_repo = ProductRepository()
        
        # Check if category is used by any product
        products = product_repo.get_by_category(category_id)
        if len(products) > 0:
            raise HTTPException(status_code=400, detail=f"Cannot delete category: {len(products)} product(s) are using it")
        
        repo = CategoryRepository()
        success = repo.delete_by_id_str(category_id)
        if not success:
            raise HTTPException(status_code=404, detail="Category not found")
        return {"message": "Category deleted successfully"}
