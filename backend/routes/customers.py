from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import get_current_user
from models.customer import Customer, CustomerCreate

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post("", response_model=Customer)
async def create_customer(customer_data: CustomerCreate, current_user: dict = Depends(get_current_user)):
    """Create a new customer"""
    customer_dict = customer_data.model_dump()
    customer_dict['tenant_id'] = current_user['tenant_id']
    customer_obj = Customer(**customer_dict)
    
    doc = customer_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.customers.insert_one(doc)
    return customer_obj

@router.get("", response_model=List[Customer])
async def get_customers(current_user: dict = Depends(get_current_user)):
    """Get all customers"""
    customers = await db.customers.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for customer in customers:
        if isinstance(customer['created_at'], str):
            customer['created_at'] = datetime.fromisoformat(customer['created_at'])
    return customers

@router.get("/{customer_id}", response_model=Customer)
async def get_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific customer"""
    customer = await db.customers.find_one({"id": customer_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if isinstance(customer['created_at'], str):
        customer['created_at'] = datetime.fromisoformat(customer['created_at'])
    return Customer(**customer)

@router.put("/{customer_id}", response_model=Customer)
async def update_customer(customer_id: str, customer_data: CustomerCreate, current_user: dict = Depends(get_current_user)):
    """Update a customer"""
    existing = await db.customers.find_one({"id": customer_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    update_data = customer_data.model_dump()
    
    await db.customers.update_one({"id": customer_id}, {"$set": update_data})
    
    updated_customer = await db.customers.find_one({"id": customer_id}, {"_id": 0})
    if isinstance(updated_customer['created_at'], str):
        updated_customer['created_at'] = datetime.fromisoformat(updated_customer['created_at'])
    return Customer(**updated_customer)

@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a customer"""
    result = await db.customers.delete_one({"id": customer_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}
