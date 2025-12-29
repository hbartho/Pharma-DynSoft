from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import hash_password, require_admin
from models.user import User, UserCreate, UserUpdate, UserResponse
from routes.auth import normalize_user_data

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("")
async def get_users(current_user: dict = Depends(require_admin)):
    """Get all users (Admin only)"""
    users = await db.users.find({"tenant_id": current_user['tenant_id']}, {"_id": 0, "password": 0}).to_list(1000)
    result = []
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        if 'is_active' not in user:
            user['is_active'] = True
        # Normaliser les données
        user = normalize_user_data(user)
        result.append(user)
    return result

@router.get("/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Get a specific user (Admin only)"""
    user = await db.users.find_one({"id": user_id, "tenant_id": current_user['tenant_id']}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    if 'is_active' not in user:
        user['is_active'] = True
    # Normaliser les données
    user = normalize_user_data(user)
    return user

@router.post("")
async def create_user_admin(user_data: UserCreate, current_user: dict = Depends(require_admin)):
    """Create a new user (Admin only)"""
    existing_user = await db.users.find_one({"email": user_data.email, "tenant_id": user_data.tenant_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Vérifier l'unicité du code employé
    existing_code = await db.users.find_one({"employee_code": user_data.employee_code, "tenant_id": user_data.tenant_id})
    if existing_code:
        raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
    
    if user_data.role not in ["admin", "pharmacien", "caissier"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be: admin, pharmacien, or caissier")
    
    user_dict = user_data.model_dump()
    hashed_password = hash_password(user_dict.pop("password"))
    user_obj = User(**user_dict)
    
    doc = user_obj.model_dump()
    doc['password'] = hashed_password
    doc['created_at'] = doc['created_at'].isoformat()
    doc['is_active'] = True
    
    await db.users.insert_one(doc)
    
    return {
        "id": user_obj.id,
        "email": user_obj.email,
        "first_name": user_obj.first_name,
        "last_name": user_obj.last_name,
        "employee_code": user_obj.employee_code,
        "role": user_obj.role,
        "tenant_id": user_obj.tenant_id,
        "is_active": True,
        "created_at": user_obj.created_at
    }

@router.put("/{user_id}")
async def update_user(user_id: str, user_update: UserUpdate, current_user: dict = Depends(require_admin)):
    """Update a user (Admin only)"""
    existing = await db.users.find_one({"id": user_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent admin from deactivating themselves
    if user_id == current_user['user_id'] and user_update.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    # Validate role if provided
    if user_update.role and user_update.role not in ["admin", "pharmacien", "caissier"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be: admin, pharmacien, or caissier")
    
    # Vérifier l'unicité du code employé si modifié
    if user_update.employee_code:
        existing_code = await db.users.find_one({
            "employee_code": user_update.employee_code, 
            "tenant_id": current_user['tenant_id'],
            "id": {"$ne": user_id}
        })
        if existing_code:
            raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
    
    update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    if 'is_active' not in updated_user:
        updated_user['is_active'] = True
    
    # Normaliser les données
    updated_user = normalize_user_data(updated_user)
    return updated_user

@router.delete("/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Delete a user (Admin only)"""
    if user_id == current_user['user_id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@router.put("/{user_id}/password")
async def change_user_password(user_id: str, new_password: str, current_user: dict = Depends(require_admin)):
    """Change a user's password (Admin only)"""
    existing = await db.users.find_one({"id": user_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_password = hash_password(new_password)
    await db.users.update_one({"id": user_id}, {"$set": {"password": hashed_password}})
    
    return {"message": "Password updated successfully"}
