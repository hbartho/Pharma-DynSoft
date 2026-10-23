"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from datetime import datetime, timezone
import os

from auth import hash_password, verify_password, create_access_token, get_current_user, generate_session_id, check_login_lockout, record_failed_login, clear_login_attempts
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
    from auth import require_admin
    from database.repositories import UserRepository
    from database.tenant_context import set_current_tenant, get_current_tenant, DEFAULT_TENANT
    from database.directory import get_directory_entry, upsert_directory_entry, is_tenant_active
    
    @router.post("/register", response_model=User)
    def register(user_data: UserCreate, current_user: dict = Depends(require_admin)):
        """Register a new user in the current pharmacy (Admin only)"""
        tenant = get_current_tenant()
        repo = UserRepository(tenant)
        email = user_data.email.strip().lower()
        
        directory_entry = get_directory_entry(email)
        if directory_entry:
            raise HTTPException(status_code=400, detail="Email already registered")
        existing_user = repo.get_by_email(email) or repo.get_by_email(user_data.email)
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
        user_dict['email'] = email
        user_dict['tenant_id'] = tenant
        if not user_dict.get('name'):
            user_dict['name'] = f"{user_data.first_name} {user_data.last_name}".strip()
        
        result = repo.create(user_dict)
        upsert_directory_entry(email, tenant)
        result['tenant_id'] = tenant
        result = normalize_user_data(result)
        return User(**result)
    
    @router.post("/login", response_model=Token)
    def login(credentials: UserLogin, request: Request):
        """Login and get access token (multi-pharmacies: le tenant est détecté via l'email)"""
        email = credentials.email.strip().lower()
        forwarded = request.headers.get("x-forwarded-for", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        check_login_lockout(client_ip, email)
        directory_entry = get_directory_entry(email)
        
        # --- Super Admin (plateforme DynSoft) ---
        if directory_entry and directory_entry.get('is_super_admin'):
            if not directory_entry.get('password_hash') or not verify_password(credentials.password, directory_entry['password_hash']):
                record_failed_login(client_ip, email)
                raise HTTPException(status_code=401, detail="Incorrect email or password")
            clear_login_attempts(client_ip, email)
            
            session_id = generate_session_id()
            access_token = create_access_token(
                data={
                    "sub": directory_entry['id'],
                    "tenant_id": None,
                    "role": "super_admin",
                    "employee_code": "SUPER",
                    "name": directory_entry.get('name') or "Super Admin",
                    "email": email,
                },
                session_id=session_id
            )
            super_user = User(
                id=directory_entry['id'],
                email=email,
                first_name=directory_entry.get('name') or "Super",
                last_name="Admin" if not directory_entry.get('name') else "",
                employee_code="SUPER",
                role="super_admin",
                tenant_id="platform",
                is_active=True,
            )
            return Token(access_token=access_token, token_type="bearer", user=super_user)
        
        # --- Utilisateur de pharmacie ---
        tenant_slug = directory_entry['tenant_slug'] if directory_entry and directory_entry.get('tenant_slug') else DEFAULT_TENANT
        
        if tenant_slug != DEFAULT_TENANT and not is_tenant_active(tenant_slug):
            raise HTTPException(status_code=403, detail="Cette pharmacie est désactivée. Contactez DynSoft.")
        
        set_current_tenant(tenant_slug)
        repo = UserRepository(tenant_slug)
        
        user = repo.get_by_email(credentials.email)
        if not user:
            user = repo.get_by_email(email)
        if not user or not verify_password(credentials.password, user['password']):
            record_failed_login(client_ip, email)
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        clear_login_attempts(client_ip, email)
        
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
                "tenant_id": tenant_slug,
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
        user_response['tenant_id'] = tenant_slug
        
        return Token(access_token=access_token, token_type="bearer", user=User(**user_response))
    
    @router.get("/me", response_model=UserResponse)
    def get_current_user_info(current_user: dict = Depends(get_current_user)):
        """Get current user information"""
        if current_user.get('role') == 'super_admin':
            return UserResponse(
                id=current_user['user_id'],
                email=current_user.get('email') or '',
                first_name=current_user.get('name') or 'Super',
                last_name='Admin',
                employee_code='SUPER',
                role='super_admin',
                tenant_id='platform',
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
        
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
        user['tenant_id'] = get_current_tenant()
        
        # Normaliser les données utilisateur
        user = normalize_user_data(user)
        
        return UserResponse(**user)
    
    @router.put("/change-password")
    def change_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
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
    def logout(current_user: dict = Depends(get_current_user)):
        """Logout and invalidate the current session"""
        # Pour PostgreSQL, on ne fait rien de spécial car on ne stocke pas les sessions
        return {"message": "Déconnexion réussie"}
    
    @router.get("/verify-session")
    def verify_session(current_user: dict = Depends(get_current_user)):
        """Verify if the current session is still valid"""
        return {"valid": True, "user_id": current_user['user_id']}

