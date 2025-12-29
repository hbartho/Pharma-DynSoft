from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import require_role, get_current_user
from models.category import Category, CategoryCreate

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("", response_model=Category)
async def create_category(category_data: CategoryCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a new category"""
    category_dict = category_data.model_dump()
    category_dict['tenant_id'] = current_user['tenant_id']
    category_obj = Category(**category_dict)
    
    doc = category_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.categories.insert_one(doc)
    return category_obj

@router.get("", response_model=List[Category])
async def get_categories(current_user: dict = Depends(get_current_user)):
    """Get all categories"""
    categories = await db.categories.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for category in categories:
        if isinstance(category.get('created_at'), str):
            category['created_at'] = datetime.fromisoformat(category['created_at'])
    return categories

@router.get("/{category_id}", response_model=Category)
async def get_category(category_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific category"""
    category = await db.categories.find_one({"id": category_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    if isinstance(category.get('created_at'), str):
        category['created_at'] = datetime.fromisoformat(category['created_at'])
    return Category(**category)

@router.put("/{category_id}", response_model=Category)
async def update_category(category_id: str, category_data: CategoryCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Update a category"""
    existing = await db.categories.find_one({"id": category_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    
    update_data = category_data.model_dump()
    await db.categories.update_one({"id": category_id}, {"$set": update_data})
    
    updated_category = await db.categories.find_one({"id": category_id}, {"_id": 0})
    if isinstance(updated_category.get('created_at'), str):
        updated_category['created_at'] = datetime.fromisoformat(updated_category['created_at'])
    return Category(**updated_category)

@router.delete("/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Delete a category"""
    # Check if category is used by any product
    products_using = await db.products.count_documents({"category_id": category_id, "tenant_id": current_user['tenant_id']})
    if products_using > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete category: {products_using} product(s) are using it")
    
    result = await db.categories.delete_one({"id": category_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"message": "Category deleted successfully"}
