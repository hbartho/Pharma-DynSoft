"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from auth import get_current_user, require_role, require_open_shift
from models.customer import Customer, CustomerCreate, CustomerUpdate
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/customers", tags=["Customers"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import CustomerRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Customer as CustomerModel
    from sqlalchemy import or_, desc
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    @router.get("/paginated")
    async def get_customers_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None, description="all, active, inactive"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les clients avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(CustomerModel)
            
            # Filtre recherche
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        CustomerModel.name.ilike(search_term),
                        CustomerModel.phone.ilike(search_term),
                        CustomerModel.email.ilike(search_term)
                    )
                )
            
            # Filtre statut
            if status == 'active':
                query = query.filter(CustomerModel.is_active == True)
            elif status == 'inactive':
                query = query.filter(CustomerModel.is_active == False)
            
            total = query.count()
            query = query.order_by(CustomerModel.name.asc())
            
            offset = (page - 1) * limit
            customers_orm = query.offset(offset).limit(limit).all()
            
            customers = []
            for c in customers_orm:
                customers.append({
                    "id": str(c.id),
                    "name": c.name,
                    "phone": c.phone,
                    "email": c.email,
                    "address": c.address,
                    "notes": c.notes,
                    "is_active": c.is_active if c.is_active is not None else True,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": customers,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.post("", response_model=Customer)
    async def create_customer(
        customer_data: CustomerCreate, 
        current_user: dict = Depends(get_current_user),
        _shift_check: dict = Depends(require_open_shift)
    ):
        """Create a new customer"""
        repo = CustomerRepository()
        data = customer_data.model_dump()
        result = repo.create(data)
        return Customer(**result)
    
    @router.get("", response_model=List[Customer])
    async def get_customers(current_user: dict = Depends(get_current_user)):
        """Get all customers"""
        repo = CustomerRepository()
        customers = repo.get_all()
        return [Customer(**c) for c in customers]
    
    @router.get("/{customer_id}", response_model=Customer)
    async def get_customer(customer_id: str, current_user: dict = Depends(get_current_user)):
        """Get a specific customer"""
        repo = CustomerRepository()
        customer = repo.get_by_id_str(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return Customer(**customer)
    
    @router.put("/{customer_id}", response_model=Customer)
    async def update_customer(customer_id: str, customer_data: CustomerUpdate, current_user: dict = Depends(get_current_user)):
        """Update a customer"""
        repo = CustomerRepository()
        # Filtrer les champs None pour ne pas écraser les données existantes
        update_data = {k: v for k, v in customer_data.model_dump().items() if v is not None}
        result = repo.update_by_id_str(customer_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Customer not found")
        return Customer(**result)
    
    @router.delete("/{customer_id}")
    async def delete_customer(customer_id: str, current_user: dict = Depends(require_role(["admin"]))):
        """Delete a customer (Admin only)"""
        repo = CustomerRepository()
        success = repo.delete_by_id_str(customer_id)
        if not success:
            raise HTTPException(status_code=404, detail="Customer not found")
        return {"message": "Customer deleted successfully"}
    
    @router.patch("/{customer_id}/toggle-status", response_model=dict)
    async def toggle_customer_status(customer_id: str, current_user: dict = Depends(get_current_user)):
        """Activer/Désactiver un client (Admin uniquement)"""
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Seul un administrateur peut activer/désactiver un client")
        
        repo = CustomerRepository()
        customer = repo.get_by_id_str(customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Client non trouvé")
        
        new_status = not customer.get('is_active', True)
        result = repo.update_by_id_str(customer_id, {"is_active": new_status})
        
        return {
            "id": customer_id,
            "is_active": new_status,
            "message": f"Client {'activé' if new_status else 'désactivé'} avec succès"
        }
