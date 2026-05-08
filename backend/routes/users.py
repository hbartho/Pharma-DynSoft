"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
import os
import uuid

from auth import hash_password, require_admin
from models.user import User, UserCreate, UserUpdate, UserResponse

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/users", tags=["User Management"])

def normalize_user_data(user: dict) -> dict:
    """Normalise les données utilisateur pour la compatibilité avec l'ancien format"""
    if 'name' in user and 'first_name' not in user:
        name_parts = user['name'].split(' ', 1)
        user['first_name'] = name_parts[0]
        user['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    
    if 'employee_code' not in user or not user.get('employee_code'):
        role_prefix = {'admin': 'ADM', 'pharmacien': 'PHA', 'caissier': 'CAI'}.get(user.get('role', ''), 'EMP')
        user['employee_code'] = f"{role_prefix}-{user['id'][:4].upper()}"
    
    if 'first_name' not in user:
        user['first_name'] = 'Utilisateur'
    if 'last_name' not in user:
        user['last_name'] = ''
    
    return user

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import UserRepository
    
    @router.get("")
    async def get_users(current_user: dict = Depends(require_admin)):
        """Get all users (Admin only)"""
        repo = UserRepository()
        users = repo.get_all(include_inactive=True)
        
        result = []
        for user in users:
            user = {k: v for k, v in user.items() if k != 'password'}
            user['tenant_id'] = 'pharmacie_centrale'
            if 'is_active' not in user:
                user['is_active'] = True
            user = normalize_user_data(user)
            result.append(user)
        return result
    
    @router.get("/{user_id}")
    async def get_user(user_id: str, current_user: dict = Depends(require_admin)):
        """Get a specific user (Admin only)"""
        repo = UserRepository()
        user = repo.get_by_id_str(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = {k: v for k, v in user.items() if k != 'password'}
        user['tenant_id'] = 'pharmacie_centrale'
        if 'is_active' not in user:
            user['is_active'] = True
        user = normalize_user_data(user)
        return user
    
    @router.post("")
    async def create_user_admin(user_data: UserCreate, current_user: dict = Depends(require_admin)):
        """Create a new user (Admin only)"""
        repo = UserRepository()
        
        existing_user = repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        existing_code = repo.get_by_employee_code(user_data.employee_code)
        if existing_code:
            raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
        
        if user_data.role not in ["admin", "pharmacien", "caissier"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be: admin, pharmacien, or caissier")
        
        user_dict = user_data.model_dump()
        password = user_dict.pop("password")
        hashed_password = hash_password(password)
        user_dict['password'] = hashed_password
        
        result = repo.create(user_dict)
        
        return {
            "id": result['id'],
            "email": result['email'],
            "first_name": result.get('first_name', result.get('name', '').split()[0] if result.get('name') else ''),
            "last_name": result.get('last_name', ''),
            "employee_code": result['employee_code'],
            "role": result['role'],
            "tenant_id": 'pharmacie_centrale',
            "is_active": result.get('is_active', True),
            "created_at": result.get('created_at')
        }
    
    @router.put("/{user_id}")
    async def update_user(user_id: str, user_update: UserUpdate, current_user: dict = Depends(require_admin)):
        """Update a user (Admin only)"""
        repo = UserRepository()
        
        existing = repo.get_by_id_str(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        if user_id == current_user['user_id'] and user_update.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
        
        if user_update.role and user_update.role not in ["admin", "pharmacien", "caissier"]:
            raise HTTPException(status_code=400, detail="Invalid role. Must be: admin, pharmacien, or caissier")
        
        if user_update.employee_code:
            existing_code = repo.get_by_employee_code(user_update.employee_code)
            if existing_code and existing_code['id'] != user_id:
                raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
        
        update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
        
        if update_data:
            repo.update(uuid.UUID(user_id), update_data)
        
        updated_user = repo.get_by_id_str(user_id)
        updated_user = {k: v for k, v in updated_user.items() if k != 'password'}
        updated_user['tenant_id'] = 'pharmacie_centrale'
        if 'is_active' not in updated_user:
            updated_user['is_active'] = True
        updated_user = normalize_user_data(updated_user)
        return updated_user
    
    @router.delete("/{user_id}")
    async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
        """Delete a user (Admin only)"""
        if user_id == current_user['user_id']:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        repo = UserRepository()
        existing = repo.get_by_id_str(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        repo.delete(uuid.UUID(user_id))
        return {"message": "User deleted successfully"}
    
    @router.patch("/{user_id}/toggle-status")
    async def toggle_user_status(user_id: str, current_user: dict = Depends(require_admin)):
        """Toggle user active status (Admin only)"""
        if user_id == current_user['user_id']:
            raise HTTPException(status_code=400, detail="Vous ne pouvez pas désactiver votre propre compte")
        
        repo = UserRepository()
        existing = repo.get_by_id_str(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        current_status = existing.get('is_active', True)
        new_status = not current_status
        
        repo.update(uuid.UUID(user_id), {'is_active': new_status})
        
        updated_user = repo.get_by_id_str(user_id)
        updated_user = {k: v for k, v in updated_user.items() if k != 'password'}
        updated_user['tenant_id'] = 'pharmacie_centrale'
        updated_user = normalize_user_data(updated_user)
        return updated_user
    
    @router.put("/{user_id}/password")
    async def change_user_password(user_id: str, new_password: str, current_user: dict = Depends(require_admin)):
        """Change a user's password (Admin only)"""
        repo = UserRepository()
        existing = repo.get_by_id_str(user_id)
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")
        
        hashed_password = hash_password(new_password)
        repo.update(uuid.UUID(user_id), {"password_hash": hashed_password})
        
        return {"message": "Password updated successfully"}

