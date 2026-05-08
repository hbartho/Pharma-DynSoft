"""
Authentication Module - PostgreSQL Only
"""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
import jwt
import uuid
from typing import List
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Role hierarchy for RBAC
ROLE_HIERARCHY = {
    "admin": 3,
    "pharmacien": 2,
    "caissier": 1
}

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def create_access_token(data: dict, session_id: str = None) -> str:
    """Create a JWT access token with session ID"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    if session_id:
        to_encode.update({"session_id": session_id})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# PostgreSQL Implementation
from database.repositories import UserRepository

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get the current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id", "default")
        role: str = payload.get("role")
        employee_code: str = payload.get("employee_code")
        session_id: str = payload.get("session_id")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        # Vérifier que l'utilisateur existe
        repo = UserRepository()
        user = repo.get_by_id_str(user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
        
        return {
            "user_id": user_id, 
            "tenant_id": tenant_id, 
            "role": role,
            "employee_code": employee_code,
            "session_id": session_id,
            "name": user.get("name", user.get("email", "Unknown")),
            "email": user.get("email")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_open_shift(current_user: dict = Depends(get_current_user)):
    """Dependency to require an open shift for operations (Admins exempt)."""
    if current_user.get('role') == 'admin':
        return current_user
    
    from database.repositories_extended import ShiftRepository
    repo = ShiftRepository()
    
    user_id = current_user.get('user_id')
    open_shift = repo.get_active_by_user_str(user_id)
    
    if not open_shift:
        raise HTTPException(
            status_code=403,
            detail="SHIFT_REQUIRED: Vous devez ouvrir un shift de caisse avant de pouvoir effectuer cette opération."
        )
    
    current_user['shift_id'] = open_shift.get('id')
    return current_user


# Common functions
def require_role(allowed_roles: List[str]):
    """Dependency to check if user has required role"""
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user['role'] not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Permission denied. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

async def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to check if user is admin"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
