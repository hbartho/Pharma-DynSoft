"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
import os

from auth import hash_password, verify_password, create_access_token, get_current_user, generate_session_id
from models.user import User, UserCreate, UserLogin, Token, UserResponse

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/auth", tags=["Authentication"])

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

def normalize_user_data(user: dict) -> dict:
    """Normalise les données utilisateur pour la compatibilité avec l'ancien format"""
    # Si l'utilisateur a l'ancien format (name), le convertir
    if 'name' in user and 'first_name' not in user:
        name_parts = user['name'].split(' ', 1)
        user['first_name'] = name_parts[0]
        user['last_name'] = name_parts[1] if len(name_parts) > 1 else ''
    
    # Générer un code employé si absent
    if 'employee_code' not in user or not user.get('employee_code'):
        # Générer un code basé sur le rôle et un ID court
        role_prefix = {'admin': 'ADM', 'pharmacien': 'PHA', 'caissier': 'CAI'}.get(user.get('role', ''), 'EMP')
        user['employee_code'] = f"{role_prefix}-{user['id'][:4].upper()}"
    
    # Valeurs par défaut
    if 'first_name' not in user:
        user['first_name'] = 'Utilisateur'
    if 'last_name' not in user:
        user['last_name'] = ''
    
    return user

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import UserRepository
    
    @router.post("/register", response_model=User)
    async def register(user_data: UserCreate):
        """Register a new user"""
        repo = UserRepository()
        
        existing_user = repo.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Vérifier l'unicité du code employé
        existing_code = repo.get_by_employee_code(user_data.employee_code)
        if existing_code:
            raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
        
        user_dict = user_data.model_dump()
        password = user_dict.pop("password")
        hashed_password = hash_password(password)
        user_dict['password'] = hashed_password
        
        result = repo.create(user_dict)
        return User(**result)
    
    @router.post("/login", response_model=Token)
    async def login(credentials: UserLogin):
        """Login and get access token"""
        repo = UserRepository()
        
        user = repo.get_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user['password']):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        # Vérifier si l'utilisateur est actif
        if user.get('is_active') == False:
            raise HTTPException(status_code=401, detail="Ce compte est désactivé")
        
        # Normaliser les données utilisateur avant de créer le token
        user = normalize_user_data(user)
        
        # Générer un nouvel ID de session unique
        session_id = generate_session_id()
        
        # Pour PostgreSQL, on ne stocke pas la session dans la DB pour simplifier
        # TODO: Implémenter si nécessaire
        
        access_token = create_access_token(
            data={
                "sub": user['id'], 
                "tenant_id": "pharmacie_centrale",  # Tenant par défaut pour PostgreSQL
                "role": user['role'],
                "employee_code": user.get('employee_code', '')
            },
            session_id=session_id
        )
        
        # Retirer le mot de passe de la réponse
        user_response = {k: v for k, v in user.items() if k != 'password'}
        
        # S'assurer que created_at est un datetime
        if isinstance(user_response.get('created_at'), str):
            user_response['created_at'] = datetime.fromisoformat(user_response['created_at'])
        elif user_response.get('created_at') is None:
            user_response['created_at'] = datetime.now(timezone.utc)
        
        # Ajouter tenant_id pour la compatibilité
        user_response['tenant_id'] = 'pharmacie_centrale'
        
        return Token(access_token=access_token, token_type="bearer", user=User(**user_response))
    
    @router.get("/me", response_model=UserResponse)
    async def get_current_user_info(current_user: dict = Depends(get_current_user)):
        """Get current user information"""
        repo = UserRepository()
        
        user = repo.get_by_id_str(current_user['user_id'])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Retirer le mot de passe
        user = {k: v for k, v in user.items() if k != 'password'}
        
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        
        if 'is_active' not in user:
            user['is_active'] = True
        
        # Ajouter tenant_id pour la compatibilité
        user['tenant_id'] = 'pharmacie_centrale'
        
        # Normaliser les données utilisateur
        user = normalize_user_data(user)
        
        return UserResponse(**user)
    
    @router.put("/change-password")
    async def change_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
        """Change the current user's password"""
        repo = UserRepository()
        
        user = repo.get_by_id_str(current_user['user_id'])
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
        
        # Vérifier le mot de passe actuel
        if not verify_password(password_data.current_password, user['password']):
            raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
        
        # Valider le nouveau mot de passe
        if len(password_data.new_password) < 6:
            raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 6 caractères")
        
        # Mettre à jour le mot de passe
        import uuid
        new_hashed_password = hash_password(password_data.new_password)
        repo.update(uuid.UUID(current_user['user_id']), {"password": new_hashed_password})
        
        return {"message": "Mot de passe mis à jour avec succès"}
    
    @router.post("/logout")
    async def logout(current_user: dict = Depends(get_current_user)):
        """Logout and invalidate the current session"""
        # Pour PostgreSQL, on ne fait rien de spécial car on ne stocke pas les sessions
        return {"message": "Déconnexion réussie"}
    
    @router.get("/verify-session")
    async def verify_session(current_user: dict = Depends(get_current_user)):
        """Verify if the current session is still valid"""
        return {"valid": True, "user_id": current_user['user_id']}

