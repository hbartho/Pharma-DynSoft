"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os

from auth import require_role, get_current_user, require_open_shift
from models.supply import Supply, SupplyCreate, SupplyUpdate, SupplyItem, SupplyItemCreate

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/supplies", tags=["Supplies"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Supply as SupplyModel, SupplyItem as SupplyItemModel, Product, Category, Supplier
    from database.repositories import ProductRepository, CategoryRepository, SupplierRepository
    from sqlalchemy import desc, or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def supply_to_dict(s, include_items=True) -> dict:
        if s is None:
            return None
        
        # Compter les items même si on ne les inclut pas dans le résultat
        items_count = len(s.items) if s.items else 0
        
        result = {
            "id": str(s.id),
            "supply_number": s.supply_number,
            "supplier_id": str(s.supplier_id) if s.supplier_id else None,
            "supplier_name": None,
            "total_amount": s.total_amount,
            "items_count": items_count,  # Toujours inclure le comptage
            "is_validated": s.is_validated,
            "delivery_note_number": s.delivery_note_number,
            "invoice_number": s.invoice_number,
            "purchase_order_ref": s.purchase_order_ref,
            "notes": s.notes,
            "created_by": s.created_by,
            "created_by_name": s.created_by,
            "validated_by": s.validated_by,
            "validated_by_name": s.validated_by,
            "supply_date": s.supply_date,
            "created_at": s.created_at,
            "validated_at": s.validated_at,
            "tenant_id": "pharmacie_centrale",
        }
        
        if include_items and s.items:
            result["items"] = [
                {
                    "id": str(item.id),
                    "product_id": str(item.product_id),
                    "product_name": item.product_name or (item.product.name if item.product else "Produit inconnu"),
                    "quantity": item.quantity,
                    "unit_price": item.purchase_price,
                    "purchase_price": item.purchase_price,
                    "selling_price": item.selling_price,
                    "prix_public_modifie": item.selling_price,
                    "total_price": item.subtotal or (item.purchase_price * item.quantity if item.purchase_price and item.quantity else 0),
                    "subtotal": item.subtotal,
                    "lot_number": item.lot_number,
                    "date_peremption": item.expiration_date.isoformat() if item.expiration_date else None,
                    "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                    "shelf_location": item.shelf_location,
                    "rayon": item.shelf_location,
                    "tax_rate": item.tax_rate or 0,
                    "tva": item.tax_rate or 0,
                    "tva_rate": item.tax_rate or 0,
                }
                for item in s.items
            ]
        else:
            result["items"] = []
        
        return result
    
    @router.get("/paginated")
    async def get_supplies_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None, description="all, validated, pending"),
        supplier_id: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les approvisionnements avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(SupplyModel).outerjoin(Supplier, SupplyModel.supplier_id == Supplier.id)
            
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        SupplyModel.supply_number.ilike(search_term),
                        SupplyModel.invoice_number.ilike(search_term),
                        Supplier.name.ilike(search_term)
                    )
                )
            
            if supplier_id:
                try:
                    query = query.filter(SupplyModel.supplier_id == uuid.UUID(supplier_id))
                except ValueError:
                    pass
            
            if status == 'validated':
                query = query.filter(SupplyModel.is_validated == True)
            elif status == 'pending':
                query = query.filter(SupplyModel.is_validated == False)
            
            total = query.count()
            query = query.order_by(desc(SupplyModel.created_at))
            
            offset = (page - 1) * limit
            supplies_orm = query.offset(offset).limit(limit).all()
            
            # Charger les noms des fournisseurs
            supplier_repo = SupplierRepository()
            suppliers = {str(s['id']): s['name'] for s in supplier_repo.get_all(include_inactive=True)}
            
            supplies = []
            for s in supplies_orm:
                data = supply_to_dict(s, include_items=False)
                data['supplier_name'] = suppliers.get(data['supplier_id'], 'Fournisseur inconnu')
                supplies.append(data)
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": supplies,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.post("", response_model=dict)
    async def create_supply(
        supply_data: SupplyCreate,
        current_user: dict = Depends(require_open_shift)
    ):
        """Créer un nouvel approvisionnement"""
        employee_code = current_user.get("employee_code", "N/A")
        product_repo = ProductRepository()
        
        with get_session() as session:
            # Vérifier l'unicité de la combinaison (Fournisseur + Bon de livraison + Facture)
            if supply_data.supplier_id and (supply_data.delivery_note_number or supply_data.invoice_number):
                existing_query = session.query(SupplyModel).filter(
                    SupplyModel.supplier_id == uuid.UUID(supply_data.supplier_id)
                )
                
                # Vérifier le bon de livraison si fourni
                if supply_data.delivery_note_number:
                    duplicate_bl = existing_query.filter(
                        SupplyModel.delivery_note_number == supply_data.delivery_note_number
                    ).first()
                    if duplicate_bl:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Un approvisionnement avec ce fournisseur et ce numéro de bon de livraison ({supply_data.delivery_note_number}) existe déjà (Réf: {duplicate_bl.supply_number})"
                        )
                
                # Vérifier la facture si fournie
                if supply_data.invoice_number:
                    duplicate_inv = existing_query.filter(
                        SupplyModel.invoice_number == supply_data.invoice_number
                    ).first()
                    if duplicate_inv:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Un approvisionnement avec ce fournisseur et ce numéro de facture ({supply_data.invoice_number}) existe déjà (Réf: {duplicate_inv.supply_number})"
                        )
            
            # Préparer les items
            items_data = []
            total_amount = 0
            
            for item_data in supply_data.items:
                product = product_repo.get_by_id_str(item_data.product_id)
                if not product:
                    raise HTTPException(status_code=400, detail=f"Produit {item_data.product_id} non trouvé")
                
                item_total = item_data.unit_price * item_data.quantity
                total_amount += item_total
                
                # Gérer la TVA - accepter tva, tva_rate ou tax_rate (sans condition != 0)
                tax_rate_value = 0
                if item_data.tva_rate is not None:
                    tax_rate_value = float(item_data.tva_rate)
                elif item_data.tva is not None:
                    tax_rate_value = float(item_data.tva)
                elif item_data.tax_rate is not None:
                    tax_rate_value = float(item_data.tax_rate)
                
                items_data.append({
                    "product_id": item_data.product_id,
                    "product_name": product.get("name"),
                    "quantity": item_data.quantity,
                    "unit_price": item_data.unit_price,
                    "selling_price": item_data.selling_price or item_data.prix_public_modifie or item_data.unit_price * 1.3,
                    "lot_number": item_data.lot_number,
                    "expiration_date": item_data.date_peremption or item_data.expiration_date,
                    "shelf_location": item_data.shelf_location or item_data.rayon,
                    "tax_rate": tax_rate_value,
                })
            
            # Créer l'approvisionnement
            supply_id = uuid.uuid4()
            supply_number = f"APP-{str(supply_id)[:8].upper()}"
            
            supply = SupplyModel(
                id=supply_id,
                supply_number=supply_number,
                supplier_id=uuid.UUID(supply_data.supplier_id) if supply_data.supplier_id else None,
                total_amount=total_amount,
                is_validated=False,
                delivery_note_number=supply_data.delivery_note_number,
                invoice_number=supply_data.invoice_number,
                purchase_order_ref=supply_data.purchase_order_ref,
                notes=supply_data.notes,
                created_by=employee_code,
                supply_date=supply_data.supply_date or datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            session.add(supply)
            session.flush()
            
            # Ajouter les items
            for item_data in items_data:
                # Gérer selling_price avec fallback sur prix_public_modifie
                selling_price = item_data.get("selling_price") or item_data.get("prix_public_modifie") or 0
                
                # Gérer shelf_location avec fallback sur rayon
                shelf_location = item_data.get("shelf_location") or item_data.get("rayon")
                
                # Gérer tax_rate - la valeur est déjà calculée correctement
                tax_rate = item_data.get("tax_rate", 0)
                
                item = SupplyItemModel(
                    id=uuid.uuid4(),
                    supply_id=supply_id,
                    product_id=uuid.UUID(item_data["product_id"]),
                    product_name=item_data.get("product_name"),
                    quantity=item_data["quantity"],
                    purchase_price=item_data.get("unit_price", item_data.get("purchase_price", 0)),
                    selling_price=selling_price,
                    subtotal=item_data["quantity"] * item_data.get("unit_price", item_data.get("purchase_price", 0)),
                    lot_number=item_data.get("lot_number"),
                    expiration_date=item_data.get("date_peremption") or item_data.get("expiration_date") or item_data.get("expiry_date"),
                    shelf_location=shelf_location,
                    tax_rate=tax_rate
                )
                session.add(item)
            
            session.commit()
            session.refresh(supply)
            
            return supply_to_dict(supply)
    
    @router.get("")
    async def get_supplies(
        status: Optional[str] = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les approvisionnements"""
        with get_session() as session:
            query = session.query(SupplyModel)
            
            if status == "pending":
                query = query.filter(SupplyModel.is_validated == False)
            elif status == "validated":
                query = query.filter(SupplyModel.is_validated == True)
            
            supplies = query.order_by(
                SupplyModel.is_validated,
                desc(SupplyModel.created_at)
            ).all()
            
            result = []
            supplier_repo = SupplierRepository()
            
            for s in supplies:
                data = supply_to_dict(s)
                if s.supplier_id:
                    supplier = supplier_repo.get_by_id(s.supplier_id)
                    if supplier:
                        data["supplier_name"] = supplier.get("name")
                result.append(data)
            
            return result
    
    @router.get("/pending-count")
    async def get_pending_supplies_count(current_user: dict = Depends(get_current_user)):
        """Récupérer le nombre d'approvisionnements en attente"""
        with get_session() as session:
            count = session.query(SupplyModel).filter(
                SupplyModel.is_validated == False
            ).count()
            return {"count": count}
    
    @router.get("/{supply_id}")
    async def get_supply(supply_id: str, current_user: dict = Depends(get_current_user)):
        """Récupérer un approvisionnement par ID"""
        with get_session() as session:
            supply = session.query(SupplyModel).filter(
                SupplyModel.id == uuid.UUID(supply_id)
            ).first()
            
            if not supply:
                raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
            
            data = supply_to_dict(supply)
            
            if supply.supplier_id:
                supplier_repo = SupplierRepository()
                supplier = supplier_repo.get_by_id(supply.supplier_id)
                if supplier:
                    data["supplier_name"] = supplier.get("name")
            
            return data
    
    @router.put("/{supply_id}")
    async def update_supply(
        supply_id: str,
        supply_data: dict,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour un approvisionnement non validé"""
        with get_session() as session:
            supply = session.query(SupplyModel).filter(
                SupplyModel.id == uuid.UUID(supply_id)
            ).first()
            
            if not supply:
                raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
            
            if supply.is_validated:
                raise HTTPException(status_code=400, detail="Impossible de modifier un approvisionnement validé")
            
            # Vérifier l'unicité si les numéros changent
            new_supplier_id = supply_data.get("supplier_id") or str(supply.supplier_id) if supply.supplier_id else None
            new_delivery_note = supply_data.get("delivery_note_number")
            new_invoice = supply_data.get("invoice_number")
            
            if new_supplier_id:
                # Vérifier doublon BL
                if new_delivery_note and new_delivery_note != supply.delivery_note_number:
                    existing = session.query(SupplyModel).filter(
                        SupplyModel.supplier_id == uuid.UUID(new_supplier_id),
                        SupplyModel.delivery_note_number == new_delivery_note,
                        SupplyModel.id != uuid.UUID(supply_id)
                    ).first()
                    if existing:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Un approvisionnement avec ce fournisseur et ce BL ({new_delivery_note}) existe déjà"
                        )
                
                # Vérifier doublon Facture
                if new_invoice and new_invoice != supply.invoice_number:
                    existing = session.query(SupplyModel).filter(
                        SupplyModel.supplier_id == uuid.UUID(new_supplier_id),
                        SupplyModel.invoice_number == new_invoice,
                        SupplyModel.id != uuid.UUID(supply_id)
                    ).first()
                    if existing:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Un approvisionnement avec ce fournisseur et cette facture ({new_invoice}) existe déjà"
                        )
            
            # Mettre à jour les champs principaux
            if "supplier_id" in supply_data and supply_data["supplier_id"]:
                supply.supplier_id = uuid.UUID(supply_data["supplier_id"])
            if "delivery_note_number" in supply_data:
                supply.delivery_note_number = supply_data["delivery_note_number"]
            if "invoice_number" in supply_data:
                supply.invoice_number = supply_data["invoice_number"]
            if "notes" in supply_data:
                supply.notes = supply_data["notes"]
            
            # Mettre à jour les items si fournis
            if "items" in supply_data:
                # Supprimer les anciens items
                session.query(SupplyItemModel).filter(
                    SupplyItemModel.supply_id == uuid.UUID(supply_id)
                ).delete()
                
                # Créer les nouveaux items
                total_amount = 0
                for item_data in supply_data["items"]:
                    subtotal = item_data["quantity"] * item_data.get("unit_price", item_data.get("purchase_price", 0))
                    total_amount += subtotal
                    
                    # Gérer selling_price avec fallback sur prix_public_modifie
                    selling_price = item_data.get("selling_price") or item_data.get("prix_public_modifie") or 0
                    
                    # Gérer shelf_location avec fallback sur rayon
                    shelf_location = item_data.get("shelf_location") or item_data.get("rayon")
                    
                    
                    # Gérer tax_rate - vérifier tous les noms possibles (sans exiger != 0)
                    tax_rate = 0
                    if item_data.get("tva_rate") is not None:
                        tax_rate = float(item_data.get("tva_rate"))
                    elif item_data.get("tva") is not None:
                        tax_rate = float(item_data.get("tva"))
                    elif item_data.get("tax_rate") is not None:
                        tax_rate = float(item_data.get("tax_rate"))
                    
                    item = SupplyItemModel(
                        id=uuid.uuid4(),
                        supply_id=uuid.UUID(supply_id),
                        product_id=uuid.UUID(item_data["product_id"]),
                        product_name=item_data.get("product_name"),
                        quantity=item_data["quantity"],
                        purchase_price=item_data.get("unit_price", item_data.get("purchase_price", 0)),
                        selling_price=selling_price,
                        subtotal=subtotal,
                        lot_number=item_data.get("lot_number"),
                        expiration_date=item_data.get("date_peremption") or item_data.get("expiration_date"),
                        shelf_location=shelf_location,
                        tax_rate=tax_rate
                    )
                    session.add(item)
                
                supply.total_amount = total_amount
            
            session.commit()
            session.refresh(supply)
            
            return supply_to_dict(supply)

    @router.post("/{supply_id}/validate")
    async def validate_supply(
        supply_id: str,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Valider un approvisionnement et mettre à jour les stocks"""
        employee_code = current_user.get("employee_code", "N/A")
        product_repo = ProductRepository()
        
        with get_session() as session:
            supply = session.query(SupplyModel).filter(
                SupplyModel.id == uuid.UUID(supply_id)
            ).first()
            
            if not supply:
                raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
            
            if supply.is_validated:
                raise HTTPException(status_code=400, detail="Approvisionnement déjà validé")
            
            # Mettre à jour les stocks et les prix des produits
            for item in supply.items:
                product = product_repo.get_by_id(item.product_id)
                if product:
                    current_stock = product.get("stock", 0)
                    new_stock = current_stock + item.quantity
                    
                    # Préparer les données de mise à jour
                    update_data = {"stock": new_stock}
                    
                    # Mettre à jour le prix d'achat si défini
                    if item.purchase_price and item.purchase_price > 0:
                        update_data["purchase_price"] = item.purchase_price
                    
                    # Mettre à jour le prix de vente (prix public) si défini dans l'approvisionnement
                    if item.selling_price and item.selling_price > 0:
                        update_data["price"] = item.selling_price
                    
                    product_repo.update(item.product_id, update_data)
            
            # Marquer comme validé
            supply.is_validated = True
            supply.validated_at = datetime.now(timezone.utc)
            supply.validated_by = employee_code
            
            # Créer une dette fournisseur si le fournisseur est défini
            supplier_debt_created = False
            if supply.supplier_id and supply.total_amount > 0:
                from database.models_tenant import SupplierDebt, DebtStatus
                
                # Calculer la date d'échéance (30 jours par défaut)
                due_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
                
                supplier_debt = SupplierDebt(
                    id=uuid.uuid4(),
                    supplier_id=supply.supplier_id,
                    supply_id=supply.id,
                    original_amount=supply.total_amount,
                    remaining_amount=supply.total_amount,
                    status=DebtStatus.PENDING,
                    due_date=due_date,
                    payments=[],
                    notes=f"Créée automatiquement lors de la validation de l'appro {supply.supply_number}",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                session.add(supplier_debt)
                supplier_debt_created = True
            
            session.commit()
            
            return {
                "message": "Approvisionnement validé",
                "supply_id": supply_id,
                "items_count": len(supply.items),
                "supplier_debt_created": supplier_debt_created
            }
    
    @router.delete("/{supply_id}")
    async def delete_supply(
        supply_id: str,
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Supprimer un approvisionnement (admin seulement, non validé uniquement)"""
        with get_session() as session:
            supply = session.query(SupplyModel).filter(
                SupplyModel.id == uuid.UUID(supply_id)
            ).first()
            
            if not supply:
                raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
            
            if supply.is_validated:
                raise HTTPException(status_code=400, detail="Impossible de supprimer un approvisionnement validé")
            
            # Supprimer les items d'abord
            session.query(SupplyItemModel).filter(
                SupplyItemModel.supply_id == uuid.UUID(supply_id)
            ).delete()
            
            session.delete(supply)
            session.commit()
            
            return {"message": "Approvisionnement supprimé", "id": supply_id}

