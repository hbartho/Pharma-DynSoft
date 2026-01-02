from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from database import db
from auth import hash_password, verify_password, create_access_token, get_current_user
from models.user import User, UserCreate, UserLogin, Token, UserResponse

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

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user"""
    existing_user = await db.users.find_one({"email": user_data.email, "tenant_id": user_data.tenant_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Vérifier l'unicité du code employé
    existing_code = await db.users.find_one({"employee_code": user_data.employee_code, "tenant_id": user_data.tenant_id})
    if existing_code:
        raise HTTPException(status_code=400, detail="Ce code employé est déjà utilisé")
    
    user_dict = user_data.model_dump()
    hashed_password = hash_password(user_dict.pop("password"))
    user_obj = User(**user_dict)
    
    doc = user_obj.model_dump()
    doc['password'] = hashed_password
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user_obj

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login and get access token"""
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Normaliser les données utilisateur avant de créer le token
    user = normalize_user_data(user)
    
    access_token = create_access_token(data={
        "sub": user['id'], 
        "tenant_id": user['tenant_id'],
        "role": user['role'],
        "employee_code": user.get('employee_code', '')
    })
    
    user.pop('password')
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    # Normaliser les données utilisateur
    user = normalize_user_data(user)
    
    return Token(access_token=access_token, token_type="bearer", user=User(**user))

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    user = await db.users.find_one({"id": current_user['user_id']}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    if 'is_active' not in user:
        user['is_active'] = True
    
    # Normaliser les données utilisateur
    user = normalize_user_data(user)
    
    return UserResponse(**user)

@router.put("/change-password")
async def change_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
    """Change the current user's password"""
    # Récupérer l'utilisateur actuel
    user = await db.users.find_one({"id": current_user['user_id']})
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    
    # Vérifier le mot de passe actuel
    if not verify_password(password_data.current_password, user['password']):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect")
    
    # Valider le nouveau mot de passe
    if len(password_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Le nouveau mot de passe doit contenir au moins 6 caractères")
    
    # Mettre à jour le mot de passe
    new_hashed_password = hash_password(password_data.new_password)
    await db.users.update_one(
        {"id": current_user['user_id']},
        {"$set": {"password": new_hashed_password}}
    )
    
    return {"message": "Mot de passe mis à jour avec succès"}
