from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from passlib.context import CryptContext
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: str  # admin, pharmacien, caissier
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str
    tenant_id: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    price: float
    stock: int
    min_stock: int = 10
    category: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    barcode: Optional[str] = None
    description: Optional[str] = None
    price: float
    stock: int
    min_stock: int = 10
    category: Optional[str] = None

class StockMovement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    product_id: str
    type: str  # in, out
    quantity: int
    reason: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StockMovementCreate(BaseModel):
    product_id: str
    type: str
    quantity: int
    reason: Optional[str] = None

class Sale(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: Optional[str] = None
    items: List[Dict[str, Any]]
    total: float
    payment_method: str
    tenant_id: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SaleCreate(BaseModel):
    customer_id: Optional[str] = None
    items: List[Dict[str, Any]]
    total: float
    payment_method: str

class Customer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class Supplier(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SupplierCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class Prescription(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    customer_id: str
    doctor_name: str
    medications: List[Dict[str, Any]]
    notes: Optional[str] = None
    status: str  # pending, fulfilled
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PrescriptionCreate(BaseModel):
    customer_id: str
    doctor_name: str
    medications: List[Dict[str, Any]]
    notes: Optional[str] = None
    status: str = "pending"

class SyncLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    action: str
    payload: Dict[str, Any]
    tenant_id: str
    user_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    synced: bool = False

class SyncData(BaseModel):
    changes: List[Dict[str, Any]]

# Helper functions
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        tenant_id: str = payload.get("tenant_id")
        role: str = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"user_id": user_id, "tenant_id": tenant_id, "role": role}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Role-based access control
ROLE_HIERARCHY = {
    "admin": 3,
    "pharmacien": 2,
    "caissier": 1
}

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

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependency to check if user is admin"""
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Auth Routes
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
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

@api_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
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

# Product Routes
@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    product_dict = product_data.model_dump()
    product_dict['tenant_id'] = current_user['tenant_id']
    product_obj = Product(**product_dict)
    
    doc = product_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.products.insert_one(doc)
    return product_obj

@api_router.get("/products", response_model=List[Product])
async def get_products(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
        if isinstance(product['updated_at'], str):
            product['updated_at'] = datetime.fromisoformat(product['updated_at'])
    return products

@api_router.get("/products/search")
async def search_products(q: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    products = await db.products.find({
        "tenant_id": current_user['tenant_id'],
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"barcode": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0}).to_list(50)
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
        if isinstance(product.get('updated_at'), str):
            product['updated_at'] = datetime.fromisoformat(product['updated_at'])
    return products

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    product = await db.products.find_one({"id": product_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if isinstance(product['created_at'], str):
        product['created_at'] = datetime.fromisoformat(product['created_at'])
    if isinstance(product['updated_at'], str):
        product['updated_at'] = datetime.fromisoformat(product['updated_at'])
    return Product(**product)

@api_router.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    existing = await db.products.find_one({"id": product_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_data.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated_product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if isinstance(updated_product['created_at'], str):
        updated_product['created_at'] = datetime.fromisoformat(updated_product['created_at'])
    if isinstance(updated_product['updated_at'], str):
        updated_product['updated_at'] = datetime.fromisoformat(updated_product['updated_at'])
    return Product(**updated_product)

@api_router.delete("/products/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    result = await db.products.delete_one({"id": product_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# Stock Movement Routes
@api_router.post("/stock", response_model=StockMovement)
async def create_stock_movement(movement_data: StockMovementCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    movement_dict = movement_data.model_dump()
    movement_dict['tenant_id'] = current_user['tenant_id']
    movement_obj = StockMovement(**movement_dict)
    
    product = await db.products.find_one({"id": movement_data.product_id, "tenant_id": current_user['tenant_id']})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if movement_data.type == "in":
        new_stock = product['stock'] + movement_data.quantity
    else:
        new_stock = product['stock'] - movement_data.quantity
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")
    
    await db.products.update_one({"id": movement_data.product_id}, {"$set": {"stock": new_stock}})
    
    doc = movement_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.stock_movements.insert_one(doc)
    return movement_obj

@api_router.get("/stock", response_model=List[StockMovement])
async def get_stock_movements(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    movements = await db.stock_movements.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for movement in movements:
        if isinstance(movement['created_at'], str):
            movement['created_at'] = datetime.fromisoformat(movement['created_at'])
    return movements

@api_router.get("/stock/alerts")
async def get_stock_alerts(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    alerts = [p for p in products if p['stock'] <= p['min_stock']]
    return alerts

# Sale Routes
@api_router.post("/sales", response_model=Sale)
async def create_sale(sale_data: SaleCreate, current_user: dict = Depends(get_current_user)):
    sale_dict = sale_data.model_dump()
    sale_dict['tenant_id'] = current_user['tenant_id']
    sale_dict['user_id'] = current_user['user_id']
    sale_obj = Sale(**sale_dict)
    
    for item in sale_data.items:
        product = await db.products.find_one({"id": item['product_id'], "tenant_id": current_user['tenant_id']})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item['product_id']} not found")
        
        new_stock = product['stock'] - item['quantity']
        if new_stock < 0:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product['name']}")
        
        await db.products.update_one({"id": item['product_id']}, {"$set": {"stock": new_stock}})
    
    doc = sale_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.sales.insert_one(doc)
    return sale_obj

@api_router.get("/sales", response_model=List[Sale])
async def get_sales(current_user: dict = Depends(get_current_user)):
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for sale in sales:
        if isinstance(sale['created_at'], str):
            sale['created_at'] = datetime.fromisoformat(sale['created_at'])
    return sales

# Customer Routes
@api_router.post("/customers", response_model=Customer)
async def create_customer(customer_data: CustomerCreate, current_user: dict = Depends(get_current_user)):
    customer_dict = customer_data.model_dump()
    customer_dict['tenant_id'] = current_user['tenant_id']
    customer_obj = Customer(**customer_dict)
    
    doc = customer_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.customers.insert_one(doc)
    return customer_obj

@api_router.get("/customers", response_model=List[Customer])
async def get_customers(current_user: dict = Depends(get_current_user)):
    customers = await db.customers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for customer in customers:
        if isinstance(customer['created_at'], str):
            customer['created_at'] = datetime.fromisoformat(customer['created_at'])
    return customers

# Supplier Routes
@api_router.post("/suppliers", response_model=Supplier)
async def create_supplier(supplier_data: SupplierCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    supplier_dict = supplier_data.model_dump()
    supplier_dict['tenant_id'] = current_user['tenant_id']
    supplier_obj = Supplier(**supplier_dict)
    
    doc = supplier_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.suppliers.insert_one(doc)
    return supplier_obj

@api_router.get("/suppliers", response_model=List[Supplier])
async def get_suppliers(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    suppliers = await db.suppliers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for supplier in suppliers:
        if isinstance(supplier['created_at'], str):
            supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
    return suppliers

@api_router.get("/suppliers/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    supplier = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if isinstance(supplier['created_at'], str):
        supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
    return Supplier(**supplier)

@api_router.put("/suppliers/{supplier_id}", response_model=Supplier)
async def update_supplier(supplier_id: str, supplier_data: SupplierCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Supplier not found")
    
    update_data = supplier_data.model_dump()
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    
    updated_supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if isinstance(updated_supplier['created_at'], str):
        updated_supplier['created_at'] = datetime.fromisoformat(updated_supplier['created_at'])
    return Supplier(**updated_supplier)

@api_router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    result = await db.suppliers.delete_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}

# Prescription Routes
@api_router.post("/prescriptions", response_model=Prescription)
async def create_prescription(prescription_data: PrescriptionCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    prescription_dict = prescription_data.model_dump()
    prescription_dict['tenant_id'] = current_user['tenant_id']
    prescription_obj = Prescription(**prescription_dict)
    
    doc = prescription_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.prescriptions.insert_one(doc)
    return prescription_obj

@api_router.get("/prescriptions", response_model=List[Prescription])
async def get_prescriptions(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    prescriptions = await db.prescriptions.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for prescription in prescriptions:
        if isinstance(prescription['created_at'], str):
            prescription['created_at'] = datetime.fromisoformat(prescription['created_at'])
    return prescriptions

@api_router.put("/prescriptions/{prescription_id}/status")
async def update_prescription_status(prescription_id: str, new_status: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    result = await db.prescriptions.update_one(
        {"id": prescription_id, "tenant_id": current_user['tenant_id']},
        {"$set": {"status": new_status}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"message": "Prescription updated successfully"}

@api_router.put("/prescriptions/{prescription_id}/edit", response_model=Prescription)
async def edit_prescription(prescription_id: str, prescription_data: PrescriptionCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    existing = await db.prescriptions.find_one({"id": prescription_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    update_data = prescription_data.model_dump()
    update_data['tenant_id'] = current_user['tenant_id']
    
    await db.prescriptions.update_one({"id": prescription_id}, {"$set": update_data})
    
    updated_prescription = await db.prescriptions.find_one({"id": prescription_id}, {"_id": 0})
    if isinstance(updated_prescription['created_at'], str):
        updated_prescription['created_at'] = datetime.fromisoformat(updated_prescription['created_at'])
    return Prescription(**updated_prescription)

@api_router.delete("/prescriptions/{prescription_id}")
async def delete_prescription(prescription_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    result = await db.prescriptions.delete_one({"id": prescription_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return {"message": "Prescription deleted successfully"}

# Sync Routes
@api_router.post("/sync/push")
async def sync_push(sync_data: SyncData, current_user: dict = Depends(get_current_user)):
    for change in sync_data.changes:
        change['tenant_id'] = current_user['tenant_id']
        change['user_id'] = current_user['user_id']
        change['synced'] = True
        change['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        if change['type'] == 'product':
            if change['action'] == 'create':
                await db.products.insert_one(change['payload'])
            elif change['action'] == 'update':
                await db.products.update_one({"id": change['payload']['id']}, {"$set": change['payload']})
            elif change['action'] == 'delete':
                await db.products.delete_one({"id": change['payload']['id']})
        
        elif change['type'] == 'sale':
            if change['action'] == 'create':
                await db.sales.insert_one(change['payload'])
        
        await db.sync_logs.insert_one(change)
    
    return {"message": f"Synced {len(sync_data.changes)} changes"}

@api_router.get("/sync/pull")
async def sync_pull(since: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {"tenant_id": current_user['tenant_id']}
    if since:
        query['updated_at'] = {"$gt": since}
    
    products = await db.products.find(query, {"_id": 0}).to_list(1000)
    sales = await db.sales.find(query, {"_id": 0}).to_list(1000)
    customers = await db.customers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    return {
        "products": products,
        "sales": sales,
        "customers": customers
    }

# Reports Routes
@api_router.get("/reports/dashboard")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    today_sales = [s for s in sales if datetime.fromisoformat(s['created_at']) >= today]
    today_revenue = sum(s['total'] for s in today_sales)
    
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    low_stock_count = len([p for p in products if p['stock'] <= p['min_stock']])
    
    prescriptions = await db.prescriptions.find({"tenant_id": current_user['tenant_id'], "status": "pending"}, {"_id": 0}).to_list(1000)
    
    return {
        "today_sales_count": len(today_sales),
        "today_revenue": today_revenue,
        "total_products": len(products),
        "low_stock_count": low_stock_count,
        "pending_prescriptions": len(prescriptions)
    }

@api_router.get("/reports/sales")
async def get_sales_report(days: int = 7, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(10000)
    
    filtered_sales = [s for s in sales if datetime.fromisoformat(s['created_at']) >= start_date]
    
    daily_stats = {}
    for sale in filtered_sales:
        sale_date = datetime.fromisoformat(sale['created_at']).date().isoformat()
        if sale_date not in daily_stats:
            daily_stats[sale_date] = {"count": 0, "revenue": 0}
        daily_stats[sale_date]['count'] += 1
        daily_stats[sale_date]['revenue'] += sale['total']
    
    return {
        "period_days": days,
        "total_sales": len(filtered_sales),
        "total_revenue": sum(s['total'] for s in filtered_sales),
        "daily_stats": daily_stats
    }

# User Management Routes (Admin only)
class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    is_active: bool = True
    created_at: datetime

@api_router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(require_admin)):
    """Get all users (Admin only)"""
    users = await db.users.find({"tenant_id": current_user['tenant_id']}, {"_id": 0, "password": 0}).to_list(1000)
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
        if 'is_active' not in user:
            user['is_active'] = True
    return users

@api_router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Get a specific user (Admin only)"""
    user = await db.users.find_one({"id": user_id, "tenant_id": current_user['tenant_id']}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    if 'is_active' not in user:
        user['is_active'] = True
    return UserResponse(**user)

@api_router.post("/users", response_model=UserResponse)
async def create_user_admin(user_data: UserCreate, current_user: dict = Depends(require_admin)):
    """Create a new user (Admin only)"""
    existing_user = await db.users.find_one({"email": user_data.email, "tenant_id": user_data.tenant_id})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
    
    return UserResponse(
        id=user_obj.id,
        email=user_obj.email,
        name=user_obj.name,
        role=user_obj.role,
        tenant_id=user_obj.tenant_id,
        is_active=True,
        created_at=user_obj.created_at
    )

@api_router.put("/users/{user_id}", response_model=UserResponse)
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
    
    update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if isinstance(updated_user.get('created_at'), str):
        updated_user['created_at'] = datetime.fromisoformat(updated_user['created_at'])
    if 'is_active' not in updated_user:
        updated_user['is_active'] = True
    
    return UserResponse(**updated_user)

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    """Delete a user (Admin only)"""
    if user_id == current_user['user_id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@api_router.put("/users/{user_id}/password")
async def change_user_password(user_id: str, new_password: str, current_user: dict = Depends(require_admin)):
    """Change a user's password (Admin only)"""
    existing = await db.users.find_one({"id": user_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    hashed_password = hash_password(new_password)
    await db.users.update_one({"id": user_id}, {"$set": {"password": hashed_password}})
    
    return {"message": "Password updated successfully"}

@api_router.get("/auth/me", response_model=UserResponse)
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()