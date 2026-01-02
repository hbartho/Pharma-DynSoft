from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from auth import require_role
from models.supplier import Supplier, SupplierCreate, SupplierUpdate

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


async def get_supplier_supplies_count(supplier_id: str, tenant_id: str) -> int:
    """Compter le nombre d'approvisionnements effectués par un fournisseur"""
    count = await db.supplies.count_documents({
        "tenant_id": tenant_id,
        "supplier_id": supplier_id
    })
    return count


@router.post("", response_model=Supplier)
async def create_supplier(supplier_data: SupplierCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Créer un nouveau fournisseur"""
    supplier_dict = supplier_data.model_dump()
    supplier_dict['tenant_id'] = current_user['tenant_id']
    supplier_dict['is_active'] = True  # Actif par défaut
    supplier_obj = Supplier(**supplier_dict)
    
    doc = supplier_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.suppliers.insert_one(doc)
    return supplier_obj


@router.get("", response_model=List[Supplier])
async def get_suppliers(
    include_inactive: Optional[bool] = None,
    current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))
):
    """
    Récupérer tous les fournisseurs
    - Admin voit tous les fournisseurs (actifs et inactifs)
    - Autres utilisateurs voient uniquement les fournisseurs actifs
    - Param include_inactive: Admin peut forcer l'affichage de tous
    """
    query = {"tenant_id": current_user['tenant_id']}
    
    # Filtrer par statut actif selon le rôle
    is_admin = current_user.get('role') == 'admin'
    
    if is_admin:
        # Admin peut choisir de voir tous ou seulement les actifs
        if include_inactive is False:
            query['is_active'] = True
        # Si include_inactive=True ou None, admin voit tout
    else:
        # Non-admin voit uniquement les fournisseurs actifs
        query['is_active'] = True
    
    suppliers = await db.suppliers.find(query, {"_id": 0}).to_list(1000)
    
    for supplier in suppliers:
        if isinstance(supplier.get('created_at'), str):
            supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
        if isinstance(supplier.get('updated_at'), str):
            supplier['updated_at'] = datetime.fromisoformat(supplier['updated_at'])
        # Assurer la compatibilité avec les anciens fournisseurs sans is_active
        if 'is_active' not in supplier:
            supplier['is_active'] = True
    
    return suppliers


@router.get("/{supplier_id}", response_model=Supplier)
async def get_supplier(supplier_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))):
    """Récupérer un fournisseur spécifique"""
    query = {"id": supplier_id, "tenant_id": current_user['tenant_id']}
    
    # Non-admin ne peut voir que les fournisseurs actifs
    if current_user.get('role') != 'admin':
        query['is_active'] = True
    
    supplier = await db.suppliers.find_one(query, {"_id": 0})
    if not supplier:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    if isinstance(supplier.get('created_at'), str):
        supplier['created_at'] = datetime.fromisoformat(supplier['created_at'])
    if isinstance(supplier.get('updated_at'), str):
        supplier['updated_at'] = datetime.fromisoformat(supplier['updated_at'])
    if 'is_active' not in supplier:
        supplier['is_active'] = True
    
    return Supplier(**supplier)


@router.put("/{supplier_id}", response_model=Supplier)
async def update_supplier(
    supplier_id: str, 
    supplier_data: SupplierUpdate, 
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Mettre à jour un fournisseur"""
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    # Préparer les données de mise à jour
    update_data = {k: v for k, v in supplier_data.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    update_data['updated_by'] = current_user.get('employee_code', '')
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    
    updated_supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if isinstance(updated_supplier.get('created_at'), str):
        updated_supplier['created_at'] = datetime.fromisoformat(updated_supplier['created_at'])
    if isinstance(updated_supplier.get('updated_at'), str):
        updated_supplier['updated_at'] = datetime.fromisoformat(updated_supplier['updated_at'])
    if 'is_active' not in updated_supplier:
        updated_supplier['is_active'] = True
    
    return Supplier(**updated_supplier)


@router.patch("/{supplier_id}/toggle-status", response_model=Supplier)
async def toggle_supplier_status(
    supplier_id: str,
    current_user: dict = Depends(require_role(["admin"]))
):
    """
    Activer/Désactiver un fournisseur (Admin uniquement)
    """
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    # Inverser le statut actuel
    current_status = existing.get('is_active', True)
    new_status = not current_status
    
    update_data = {
        'is_active': new_status,
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'updated_by': current_user.get('employee_code', '')
    }
    
    await db.suppliers.update_one({"id": supplier_id}, {"$set": update_data})
    
    updated_supplier = await db.suppliers.find_one({"id": supplier_id}, {"_id": 0})
    if isinstance(updated_supplier.get('created_at'), str):
        updated_supplier['created_at'] = datetime.fromisoformat(updated_supplier['created_at'])
    if isinstance(updated_supplier.get('updated_at'), str):
        updated_supplier['updated_at'] = datetime.fromisoformat(updated_supplier['updated_at'])
    
    return Supplier(**updated_supplier)


@router.get("/{supplier_id}/can-delete")
async def check_supplier_can_delete(
    supplier_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Vérifier si un fournisseur peut être supprimé"""
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    supplies_count = await get_supplier_supplies_count(supplier_id, current_user['tenant_id'])
    
    return {
        "can_delete": supplies_count == 0,
        "supplies_count": supplies_count,
        "message": f"Ce fournisseur a effectué {supplies_count} approvisionnement(s)" if supplies_count > 0 else "Ce fournisseur peut être supprimé"
    }


@router.delete("/{supplier_id}")
async def delete_supplier(
    supplier_id: str, 
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """
    Supprimer un fournisseur
    Impossible si le fournisseur a effectué au moins un approvisionnement
    """
    existing = await db.suppliers.find_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    # Vérifier si le fournisseur a des approvisionnements
    supplies_count = await get_supplier_supplies_count(supplier_id, current_user['tenant_id'])
    
    if supplies_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer ce fournisseur : il a effectué {supplies_count} approvisionnement(s). Vous pouvez le désactiver à la place."
        )
    
    result = await db.suppliers.delete_one({"id": supplier_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fournisseur non trouvé")
    
    return {"message": "Fournisseur supprimé avec succès"}
