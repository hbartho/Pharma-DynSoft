from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from database import db
from auth import hash_password, verify_password, create_access_token, get_current_user
from models.user import User, UserCreate, UserLogin, Token, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user"""
    existing_user = await db.users.find_one({"email": user_data.email, "tenant_id": user_data.tenant_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
    
    access_token = create_access_token(data={
        "sub": user['id'], 
        "tenant_id": user['tenant_id'],
        "role": user['role']
    })
    
    user.pop('password')
    if isinstance(user['created_at'], str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
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
    return UserResponse(**user)
