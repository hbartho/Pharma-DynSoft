"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from auth import require_role, require_open_shift, get_current_user
from models.supplier import Supplier, SupplierCreate, SupplierUpdate
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import SupplierRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Supplier as SupplierModel
    from sqlalchemy import or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    @router.get("/paginated")
    async def get_suppliers_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les fournisseurs avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(SupplierModel)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        SupplierModel.name.ilike(search_term),
                        SupplierModel.phone.ilike(search_term),
                        SupplierModel.email.ilike(search_term)
                    )
                )
            
            if status == 'active':
                query = query.filter(SupplierModel.is_active == True)
            elif status == 'inactive':
                query = query.filter(SupplierModel.is_active == False)
            
            total = query.count()
            query = query.order_by(SupplierModel.name.asc())
            
            offset = (page - 1) * limit
            suppliers_orm = query.offset(offset).limit(limit).all()
            
            suppliers = []
            for s in suppliers_orm:
                suppliers.append({
                    "id": str(s.id),
                    "name": s.name,
                    "phone": s.phone,
                    "email": s.email,
                    "address": s.address,
                    "is_active": s.is_active if s.is_active is not None else True,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                })
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": suppliers,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.post("", response_model=Supplier)
    async def create_supplier(
        supplier_data: SupplierCreate, 
        current_user: dict = Depends(require_role(["admin", "pharmacien"])),
        _shift_check: dict = Depends(require_open_shift)
    ):
        """Créer un nouveau fournisseur"""
        repo = SupplierRepository()
        data = supplier_data.model_dump()
        data['is_active'] = True
        result = repo.create(data)
        return Supplier(**result)
    
    @router.get("", response_model=List[Supplier])
    async def get_suppliers(
        include_inactive: Optional[bool] = None,
        current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))
    ):
        """Récupérer tous les fournisseurs"""
        repo = SupplierRepository()
        is_admin = current_user.get('role') == 'admin'
        
        if is_admin and include_inactive is not False:
            suppliers = repo.get_all(include_inactive=True)
        else:
            suppliers = repo.get_all(include_inactive=False)
        
        return [Supplier(**s) for s in suppliers]
    
    @router.get("/{supplier_id}", response_model=Supplier)
    async def get_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))):
        """Récupérer un fournisseur spécifique"""
        repo = SupplierRepository()
        supplier = repo.get_by_id_str(supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        
        # Non-admin ne peut voir que les fournisseurs actifs
        if current_user.get('role') != 'admin' and not supplier.get('is_active', True):
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        
        return Supplier(**supplier)
    
    @router.put("/{supplier_id}", response_model=Supplier)
    async def update_supplier(
        supplier_id: str, 
        supplier_data: SupplierUpdate, 
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour un fournisseur"""
        repo = SupplierRepository()
        update_data = {k: v for k, v in supplier_data.model_dump().items() if v is not None}
        result = repo.update_by_id_str(supplier_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        return Supplier(**result)
    
    @router.patch("/{supplier_id}/toggle-status", response_model=Supplier)
    async def toggle_supplier_status(
        supplier_id: str,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Activer/Désactiver un fournisseur (Admin uniquement)"""
        repo = SupplierRepository()
        result = repo.toggle_status_by_id_str(supplier_id)
        if not result:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        return Supplier(**result)
    
    @router.get("/{supplier_id}/can-delete")
    async def check_supplier_can_delete(
        supplier_id: str,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Vérifier si un fournisseur peut être supprimé"""
        repo = SupplierRepository()
        supplier = repo.get_by_id_str(supplier_id)
        if not supplier:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        
        # TODO: Vérifier les approvisionnements dans PostgreSQL
        supplies_count = 0  # À implémenter avec SupplyRepository
        
        return {
            "can_delete": supplies_count == 0,
            "supplies_count": supplies_count,
            "message": f"Ce fournisseur a effectué {supplies_count} approvisionnement(s)" if supplies_count > 0 else "Ce fournisseur peut être supprimé"
        }
    
    @router.delete("/{supplier_id}")
    async def delete_supplier(
        supplier_id: str, 
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Supprimer un fournisseur"""
        repo = SupplierRepository()
        
        # TODO: Vérifier les approvisionnements
        
        success = repo.delete_by_id_str(supplier_id)
        if not success:
            raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
        
        return {"message": "Fournisseur supprimé avec succès"}
