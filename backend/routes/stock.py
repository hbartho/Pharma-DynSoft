"""
Routes Stock - PostgreSQL Implementation
Gère les mouvements de stock et alertes
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os

from auth import require_role, get_current_user, require_open_shift
from models.stock import StockMovement, StockMovementCreate, StockMovementType, StockSummary

router = APIRouter(prefix="/stock", tags=["Stock"])

DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Product, StockMovement as StockMovementModel, StockMovementType as SMType
    from database.repositories import ProductRepository
    from sqlalchemy import desc
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def get_product_info(product_id: str) -> dict:
        """Récupérer les infos d'un produit"""
        with get_session() as session:
            try:
                product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
            except ValueError:
                return {"name": "Produit inconnu", "stock": 0}
            
            if product:
                return {"name": product.name, "stock": product.stock or 0}
            return {"name": "Produit inconnu", "stock": 0}
    
    def get_valuation_for_product(product_id: str, method: str = "weighted_average") -> dict:
        """Calculer la valorisation du stock pour un produit"""
        with get_session() as session:
            try:
                product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
            except ValueError:
                return {"unit_cost": 0, "total_value": 0}
            
            if not product:
                return {"unit_cost": 0, "total_value": 0}
            
            current_stock = product.stock or 0
            purchase_price = product.purchase_price or product.price * 0.7 if product.price else 0
            
            if current_stock <= 0:
                return {"unit_cost": 0, "total_value": 0}
            
            unit_cost = purchase_price
            total_value = current_stock * unit_cost
            
            return {"unit_cost": unit_cost, "total_value": total_value}
    
    async def create_stock_movement(
        product_id: str,
        movement_type: str,
        movement_quantity: int,
        agent_code: str,
        reference_type: str = None,
        reference_id: str = None,
        reason: str = None,
        lot_number: str = None
    ) -> dict:
        """Créer un mouvement de stock"""
        with get_session() as session:
            # Récupérer le produit
            try:
                product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            
            if not product:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            
            # Calculer le nouveau stock
            old_stock = product.stock or 0
            
            if movement_type.upper() in ["IN", "RETURN"]:
                new_stock = old_stock + abs(movement_quantity)
            else:
                new_stock = old_stock - abs(movement_quantity)
            
            if new_stock < 0:
                raise HTTPException(status_code=400, detail="Stock insuffisant")
            
            # Mettre à jour le stock du produit
            product.stock = new_stock
            
            # Créer le mouvement
            type_enum = SMType[movement_type.upper()]
            movement = StockMovementModel(
                product_id=product.id,
                movement_type=type_enum,
                quantity=movement_quantity if movement_type.upper() in ["IN", "RETURN"] else -abs(movement_quantity),
                stock_after=new_stock,
                reference_type=reference_type,
                agent_code=agent_code,
                reason=reason
            )
            session.add(movement)
            session.commit()
            
            return {
                "id": str(movement.id),
                "product_id": str(movement.product_id),
                "product_name": product.name,
                "movement_type": movement_type,
                "quantity": movement_quantity,
                "stock_before": old_stock,
                "stock_after": new_stock,
                "created_at": movement.created_at.isoformat() if movement.created_at else None
            }
    
    # ============== ROUTES ==============
    
    @router.get("/movements/paginated")
    async def get_stock_movements_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        movement_type: Optional[str] = Query(default=None, description="all, IN, OUT, ADJUSTMENT, LOSS, RETURN"),
        product_id: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les mouvements de stock avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(StockMovementModel).outerjoin(Product, StockMovementModel.product_id == Product.id)
            
            if search:
                search_term = f"%{search}%"
                from sqlalchemy import or_
                query = query.filter(Product.name.ilike(search_term))
            
            if product_id:
                try:
                    query = query.filter(StockMovementModel.product_id == uuid.UUID(product_id))
                except ValueError:
                    pass
            
            if movement_type and movement_type != 'all':
                try:
                    type_enum = SMType[movement_type.upper()]
                    query = query.filter(StockMovementModel.movement_type == type_enum)
                except KeyError:
                    pass
            
            total = query.count()
            query = query.order_by(desc(StockMovementModel.created_at))
            
            offset = (page - 1) * limit
            movements_orm = query.offset(offset).limit(limit).all()
            
            # Récupérer les noms des produits
            product_repo = ProductRepository()
            products = {str(p['id']): p['name'] for p in product_repo.get_all()}
            
            # Mapping des types de référence vers labels
            reference_labels = {
                "sale": "Vente",
                "return": "Retour",
                "supply": "Approvisionnement",
                "adjustment": "Ajustement",
                "loss": "Perte",
                "inventory": "Inventaire",
            }
            
            def get_reference_text(m):
                ref_type = m.reference_type or ""
                reason = m.reason or ""
                if ref_type:
                    label = reference_labels.get(ref_type, ref_type.capitalize())
                    if reason:
                        return f"{label}: {reason[:30]}..." if len(reason) > 30 else f"{label}: {reason}"
                    return label
                if reason:
                    return reason[:40] + "..." if len(reason) > 40 else reason
                return "-"
            
            movements = [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "product_name": products.get(str(m.product_id), "Produit inconnu"),
                    "movement_type": m.movement_type.value if hasattr(m.movement_type, 'value') else m.movement_type,
                    "quantity": m.quantity,
                    "stock_after": m.stock_after,
                    "reference_type": m.reference_type,
                    "reference": get_reference_text(m),
                    "agent_code": m.agent_code,
                    "created_by": m.agent_code or "-",
                    "reason": m.reason,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in movements_orm
            ]
            
            # Calculer les stats globales
            all_movements = session.query(StockMovementModel).all()
            total_in = sum(m.quantity for m in all_movements if m.quantity > 0)
            total_out = sum(abs(m.quantity) for m in all_movements if m.quantity < 0)
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": movements,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1,
                "stats": {
                    "total_movements": len(all_movements),
                    "total_in": total_in,
                    "total_out": total_out,
                    "net_balance": total_in - total_out
                }
            }
    
    @router.get("/losses/paginated")
    async def get_stock_losses_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        status: Optional[str] = Query(default=None),
        reason: Optional[str] = Query(default=None),
        date_from: Optional[str] = Query(default=None),
        date_to: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les pertes de stock avec pagination pour infinite scroll"""
        with get_session() as session:
            query = session.query(StockMovementModel).outerjoin(Product, StockMovementModel.product_id == Product.id)
            
            # Filtrer uniquement les pertes (LOSS) et ajustements négatifs
            query = query.filter(StockMovementModel.movement_type == SMType.LOSS)
            
            if search:
                search_term = f"%{search}%"
                from sqlalchemy import or_
                query = query.filter(Product.name.ilike(search_term))
            
            # Filtre par statut - NON DISPONIBLE pour StockMovement
            # Les pertes n'ont pas de statut de validation dans ce modèle
            # if status and status != 'all':
            #     if status == 'pending':
            #         query = query.filter(StockMovementModel.is_validated == False)
            #     elif status == 'validated':
            #         query = query.filter(StockMovementModel.is_validated == True)
            
            # Filtre par raison
            if reason and reason != 'all':
                query = query.filter(StockMovementModel.reason == reason)
            
            # Filtre par date
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    query = query.filter(StockMovementModel.created_at >= from_date)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    to_date = datetime.strptime(date_to, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    to_date = to_date + timedelta(days=1)  # Inclure toute la journée
                    query = query.filter(StockMovementModel.created_at < to_date)
                except ValueError:
                    pass
            
            total = query.count()
            query = query.order_by(desc(StockMovementModel.created_at))
            
            offset = (page - 1) * limit
            losses_orm = query.offset(offset).limit(limit).all()
            
            # Récupérer les noms des produits
            product_repo = ProductRepository()
            products = {str(p['id']): p['name'] for p in product_repo.get_all()}
            
            # Labels des motifs
            reason_labels = {
                "expired": "Produit périmé",
                "damaged": "Produit endommagé",
                "theft": "Vol",
                "inventory_adjustment": "Ajustement inventaire",
                "broken": "Casse",
                "returned_supplier": "Retour fournisseur",
                "other": "Autre"
            }
            
            def get_reason_label(reason_code):
                if not reason_code:
                    return "Autre"
                # Extraire le code principal si format "code: details"
                main_code = reason_code.split(':')[0].strip() if ':' in reason_code else reason_code
                return reason_labels.get(main_code, reason_code)
            
            losses = [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "product_name": products.get(str(m.product_id), "Produit inconnu"),
                    "quantity": abs(m.quantity),
                    "reason": m.reason.split(':')[0].strip() if m.reason and ':' in m.reason else m.reason,
                    "reason_label": get_reason_label(m.reason),
                    "status": "validated",  # Toutes les pertes enregistrées sont validées
                    "validated_by_name": m.agent_code,
                    "agent_code": m.agent_code,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in losses_orm
            ]
            
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": losses,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.get("/losses/reasons")
    async def get_loss_reasons(current_user: dict = Depends(get_current_user)):
        """Récupérer la liste des motifs de perte possibles"""
        return [
            {"id": "expired", "label": "Produit périmé", "icon": "calendar"},
            {"id": "damaged", "label": "Produit endommagé", "icon": "package"},
            {"id": "theft", "label": "Vol", "icon": "alert-triangle"},
            {"id": "inventory_adjustment", "label": "Ajustement inventaire", "icon": "edit"},
            {"id": "broken", "label": "Casse", "icon": "x-circle"},
            {"id": "returned_supplier", "label": "Retour fournisseur", "icon": "truck"},
            {"id": "other", "label": "Autre", "icon": "help-circle"}
        ]
    
    @router.get("/losses/pending")
    async def get_pending_losses(current_user: dict = Depends(get_current_user)):
        """Récupérer les pertes en attente de validation"""
        with get_session() as session:
            # Les pertes en attente sont les mouvements LOSS avec validation_status 'pending' ou NULL
            query = session.query(StockMovementModel).filter(
                StockMovementModel.movement_type == SMType.LOSS,
                (StockMovementModel.validation_status == 'pending') | (StockMovementModel.validation_status == None)
            )
            
            losses = query.order_by(desc(StockMovementModel.created_at)).limit(50).all()
            
            product_repo = ProductRepository()
            products_data = {str(p['id']): p for p in product_repo.get_all()}
            
            # Mapping des raisons
            reason_to_code = {
                "expired": "expired", "damaged": "damaged", "theft": "theft",
                "inventory_adjustment": "inventory_adjustment", "broken": "broken",
                "returned_supplier": "returned_supplier", "other": "other",
                "Produit périmé": "expired", "Produit endommagé": "damaged",
                "Vol": "theft", "Ajustement inventaire": "inventory_adjustment",
                "Casse": "broken", "Retour fournisseur": "returned_supplier", "Autre": "other",
            }
            reason_labels = {
                "expired": "Produit périmé", "damaged": "Produit endommagé",
                "theft": "Vol", "inventory_adjustment": "Ajustement inventaire",
                "broken": "Casse", "returned_supplier": "Retour fournisseur", "other": "Autre"
            }
            
            def get_reason_info(raw_reason):
                if not raw_reason:
                    return "other", "Autre"
                # Ignorer les annotations de rejet/validation
                main_reason = raw_reason.split('\n')[0].strip()
                main_reason = main_reason.split(':')[0].strip() if ':' in main_reason else main_reason
                reason_code = reason_to_code.get(main_reason, "other")
                return reason_code, reason_labels.get(reason_code, raw_reason)
            
            result = []
            for m in losses:
                product = products_data.get(str(m.product_id), {})
                unit_price = product.get('purchase_price', 0) or (product.get('price', 0) * 0.7 if product.get('price') else 0)
                estimated_value = abs(m.quantity) * unit_price
                
                reason_code, reason_label = get_reason_info(m.reason)
                
                result.append({
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "product_name": product.get('name', 'Produit inconnu'),
                    "quantity": abs(m.quantity),
                    "reason": reason_code,
                    "reason_label": reason_label,
                    "estimated_value": estimated_value,
                    "notes": None,
                    "status": m.validation_status or "pending",
                    "declared_by_name": m.agent_code,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                })
            
            return result
    
    @router.get("/losses/history")
    async def get_losses_history(
        status: Optional[str] = None,
        reason: Optional[str] = None,
        product_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = Query(default=50, le=500),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des pertes validées/rejetées"""
        with get_session() as session:
            query = session.query(StockMovementModel).filter(
                StockMovementModel.movement_type == SMType.LOSS
            )
            
            # Filtrer par statut
            if status:
                if status == 'validated':
                    query = query.filter(StockMovementModel.validation_status == 'validated')
                elif status == 'rejected':
                    query = query.filter(StockMovementModel.validation_status == 'rejected')
                elif status == 'pending':
                    query = query.filter(
                        (StockMovementModel.validation_status == 'pending') | 
                        (StockMovementModel.validation_status == None)
                    )
            
            if reason:
                query = query.filter(StockMovementModel.reason.ilike(f"%{reason}%"))
            
            if product_id:
                try:
                    query = query.filter(StockMovementModel.product_id == uuid.UUID(product_id))
                except ValueError:
                    pass
            
            if date_from:
                try:
                    from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                    query = query.filter(StockMovementModel.created_at >= from_date)
                except:
                    pass
            
            if date_to:
                try:
                    to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                    query = query.filter(StockMovementModel.created_at <= to_date)
                except:
                    pass
            
            losses = query.order_by(desc(StockMovementModel.created_at)).limit(limit).all()
            
            product_repo = ProductRepository()
            products = {str(p['id']): p['name'] for p in product_repo.get_all()}
            
            reason_labels = {
                "expired": "Produit périmé",
                "damaged": "Produit endommagé",
                "theft": "Vol",
                "inventory_adjustment": "Ajustement inventaire",
                "broken": "Casse",
                "returned_supplier": "Retour fournisseur",
                "other": "Autre"
            }
            
            return [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "product_name": products.get(str(m.product_id), "Produit inconnu"),
                    "quantity": abs(m.quantity),
                    "reason": m.reason.split('\n')[0] if m.reason else "other",
                    "reason_label": reason_labels.get(m.reason.split('\n')[0] if m.reason else "other", m.reason or "Autre"),
                    "status": m.validation_status or "pending",
                    "validated_by": m.validated_by,
                    "validated_at": m.validated_at.isoformat() if m.validated_at else None,
                    "declared_by_name": m.agent_code,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in losses
            ]
    
    @router.get("/losses/stats")
    async def get_losses_stats(
        period: str = Query(default="month", description="day, week, month, year"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les statistiques des pertes"""
        with get_session() as session:
            from datetime import timedelta
            from sqlalchemy import func
            
            now = datetime.now(timezone.utc)
            
            # Définir la période
            if period == "day":
                start_date = now - timedelta(days=1)
            elif period == "week":
                start_date = now - timedelta(weeks=1)
            elif period == "year":
                start_date = now - timedelta(days=365)
            else:  # month par défaut
                start_date = now - timedelta(days=30)
            
            # Récupérer les pertes dans la période
            losses = session.query(StockMovementModel).filter(
                StockMovementModel.movement_type == SMType.LOSS,
                StockMovementModel.created_at >= start_date
            ).all()
            
            # Calculer les statistiques
            total_quantity = sum(abs(m.quantity) for m in losses)
            total_count = len(losses)
            
            # Calculer la valeur totale perdue
            total_value = 0
            product_repo = ProductRepository()
            products_data = {str(p['id']): p for p in product_repo.get_all()}
            
            # Mapping des raisons vers codes normalisés
            reason_to_code = {
                "expired": "expired",
                "damaged": "damaged", 
                "theft": "theft",
                "inventory_adjustment": "inventory_adjustment",
                "broken": "broken",
                "returned_supplier": "returned_supplier",
                "other": "other",
                # Labels français vers codes
                "Produit périmé": "expired",
                "Produit endommagé": "damaged",
                "Vol": "theft",
                "Ajustement inventaire": "inventory_adjustment",
                "Casse": "broken",
                "Retour fournisseur": "returned_supplier",
                "Autre": "other",
            }
            
            reason_labels = {
                "expired": "Produit périmé",
                "damaged": "Produit endommagé",
                "theft": "Vol",
                "inventory_adjustment": "Ajustement inventaire",
                "broken": "Casse",
                "returned_supplier": "Retour fournisseur",
                "other": "Autre"
            }
            
            by_reason = {}
            for m in losses:
                product = products_data.get(str(m.product_id), {})
                unit_price = product.get('purchase_price', 0) or product.get('price', 0) * 0.7 if product.get('price') else 0
                loss_value = abs(m.quantity) * unit_price
                total_value += loss_value
                
                # Normaliser la raison
                raw_reason = m.reason or "other"
                # Extraire le code principal si format "code: details"
                main_reason = raw_reason.split(':')[0].strip() if ':' in raw_reason else raw_reason
                reason_code = reason_to_code.get(main_reason, "other")
                
                if reason_code not in by_reason:
                    by_reason[reason_code] = {"count": 0, "quantity": 0, "value": 0, "label": reason_labels.get(reason_code, reason_code)}
                by_reason[reason_code]["count"] += 1
                by_reason[reason_code]["quantity"] += abs(m.quantity)
                by_reason[reason_code]["value"] += loss_value
            
            # Compter les pertes par statut (utiliser validation_status pour la cohérence)
            pending_count = session.query(func.count(StockMovementModel.id)).filter(
                StockMovementModel.movement_type == SMType.LOSS,
                (StockMovementModel.validation_status == 'pending') | (StockMovementModel.validation_status == None)
            ).scalar() or 0
            
            validated_count = session.query(func.count(StockMovementModel.id)).filter(
                StockMovementModel.movement_type == SMType.LOSS,
                StockMovementModel.validation_status == 'validated'
            ).scalar() or 0
            
            rejected_count = session.query(func.count(StockMovementModel.id)).filter(
                StockMovementModel.movement_type == SMType.LOSS,
                StockMovementModel.validation_status == 'rejected'
            ).scalar() or 0
            
            return {
                "period": period,
                "total_count": total_count,
                "total_quantity": total_quantity,
                "total_value": total_value,
                "by_reason": by_reason,
                "pending_count": pending_count,
                "validated_count": validated_count,
                "rejected_count": rejected_count
            }
    
    @router.post("/losses")
    async def declare_loss(
        product_id: str = Query(...),
        quantity: int = Query(..., ge=1),
        reason: str = Query(...),
        reason_details: Optional[str] = Query(default=None),
        lot_number: Optional[str] = Query(default=None),
        notes: Optional[str] = Query(default=None),
        current_user: dict = Depends(require_open_shift)
    ):
        """Déclarer une perte de stock"""
        employee_code = current_user.get('employee_code', 'N/A')
        
        # Combiner reason et details/notes
        full_reason = reason
        if reason_details:
            full_reason = f"{reason}: {reason_details}"
        if notes:
            full_reason = f"{full_reason} - {notes}"
        
        result = await create_stock_movement(
            product_id=product_id,
            movement_type="loss",
            movement_quantity=-abs(quantity),  # Négatif pour une perte
            agent_code=employee_code,
            reference_type="loss_declaration",
            reason=full_reason,
            lot_number=lot_number
        )
        
        return {
            "id": result.get("id"),
            "product_id": product_id,
            "quantity": quantity,
            "reason": reason,
            "status": "validated",  # Auto-validé pour l'instant
            "message": "Perte déclarée et appliquée au stock"
        }
    
    @router.post("/losses/{loss_id}/validate")
    async def validate_loss(
        loss_id: str,
        action: str = Query(..., description="validate or reject"),
        rejection_reason: Optional[str] = Query(default=None),
        current_user: dict = Depends(require_role(["admin"]))
    ):
        """Valider ou rejeter une perte (Admin uniquement)"""
        
        if action not in ["validate", "reject"]:
            raise HTTPException(status_code=400, detail="Action doit être 'validate' ou 'reject'")
        
        employee_code = current_user.get("employee_code", "N/A")
        
        with get_session() as session:
            try:
                movement = session.query(StockMovementModel).filter(
                    StockMovementModel.id == uuid.UUID(loss_id)
                ).first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Perte non trouvée")
            
            if not movement:
                raise HTTPException(status_code=404, detail="Perte non trouvée")
            
            # Vérifier que c'est bien une perte
            if movement.movement_type != SMType.LOSS:
                raise HTTPException(status_code=400, detail="Ce mouvement n'est pas une perte")
            
            # Vérifier si déjà validé/rejeté
            if movement.validation_status and movement.validation_status != 'pending':
                raise HTTPException(status_code=400, detail=f"Cette perte est déjà {movement.validation_status}")
            
            if action == "reject":
                # Rejeter = Restaurer le stock et marquer comme rejeté
                product_repo = ProductRepository()
                product = product_repo.get_by_id_str(str(movement.product_id))
                
                if product:
                    # Restaurer le stock (la perte avait soustrait du stock)
                    new_stock = (product.get('stock', 0) or 0) + abs(movement.quantity)
                    product_repo.update(str(movement.product_id), {'stock': new_stock})
                
                # Mettre à jour le statut au lieu de supprimer
                movement.validation_status = 'rejected'
                movement.validated_by = employee_code
                movement.validated_at = datetime.now(timezone.utc)
                movement.reason = f"{movement.reason or ''}\n[REJET] {rejection_reason or 'Sans raison'}".strip()
                
                session.commit()
                
                return {
                    "id": loss_id,
                    "status": "rejected",
                    "message": "Perte rejetée et stock restauré"
                }
            else:
                # Valider = Confirmer la perte
                movement.validation_status = 'validated'
                movement.validated_by = employee_code
                movement.validated_at = datetime.now(timezone.utc)
                
                session.commit()
                
                return {
                    "id": str(movement.id),
                    "status": "validated",
                    "message": "Perte validée"
                }
    
    @router.get("/movements", response_model=List[dict])
    async def get_stock_movements(
        product_id: Optional[str] = None,
        movement_type: Optional[str] = None,
        limit: int = Query(default=500, le=1000),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des mouvements de stock"""
        with get_session() as session:
            query = session.query(StockMovementModel)
            
            if product_id:
                try:
                    query = query.filter(StockMovementModel.product_id == uuid.UUID(product_id))
                except ValueError:
                    pass
            
            if movement_type:
                try:
                    type_enum = SMType[movement_type.upper()]
                    query = query.filter(StockMovementModel.movement_type == type_enum)
                except KeyError:
                    pass
            
            movements = query.order_by(desc(StockMovementModel.created_at)).limit(limit).all()
            
            # Récupérer les noms des produits
            product_repo = ProductRepository()
            products = {str(p['id']): p['name'] for p in product_repo.get_all()}
            
            return [
                {
                    "id": str(m.id),
                    "product_id": str(m.product_id),
                    "product_name": products.get(str(m.product_id), "Produit inconnu"),
                    "movement_type": m.movement_type.value if hasattr(m.movement_type, 'value') else m.movement_type,
                    "quantity": m.quantity,
                    "stock_after": m.stock_after,
                    "reference_type": m.reference_type,
                    "agent_code": m.agent_code,
                    "reason": m.reason,
                    "created_at": m.created_at.isoformat() if m.created_at else None
                }
                for m in movements
            ]
    
    @router.post("/movement", response_model=dict)
    async def create_movement(
        movement_data: StockMovementCreate,
        current_user: dict = Depends(require_open_shift)
    ):
        """Créer un mouvement de stock manuel"""
        employee_code = current_user.get('employee_code', 'N/A')
        
        result = await create_stock_movement(
            product_id=movement_data.product_id,
            movement_type=movement_data.movement_type.value,
            movement_quantity=movement_data.quantity,
            agent_code=employee_code,
            reference_type="manual",
            reason=movement_data.reason
        )
        
        return result
    
    @router.get("/alerts", response_model=List[dict])
    async def get_stock_alerts(
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les alertes de stock (produits sous le seuil)"""
        with get_session() as session:
            # Produits avec stock bas
            products = session.query(Product).filter(
                Product.is_active == True,
                Product.stock <= Product.min_stock
            ).all()
            
            alerts = []
            for p in products:
                alerts.append({
                    "product_id": str(p.id),
                    "product_name": p.name,
                    "current_stock": p.stock or 0,
                    "min_stock": p.min_stock or 10,
                    "category": p.category.name if p.category else None,
                    "alert_type": "rupture" if (p.stock or 0) == 0 else "seuil_bas"
                })
            
            return alerts
    
    @router.get("/summary", response_model=dict)
    async def get_stock_summary(
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer un résumé du stock"""
        with get_session() as session:
            products = session.query(Product).filter(Product.is_active == True).all()
            
            total_products = len(products)
            total_stock_value = 0
            low_stock_count = 0
            out_of_stock_count = 0
            
            for p in products:
                stock = p.stock or 0
                price = p.price or 0
                total_stock_value += stock * price
                
                if stock == 0:
                    out_of_stock_count += 1
                elif stock <= (p.min_stock or 10):
                    low_stock_count += 1
            
            return {
                "total_products": total_products,
                "total_stock_value": total_stock_value,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count
            }
    
    @router.get("/valuation", response_model=List[dict])
    async def get_stock_valuation(
        method: str = Query(default="weighted_average", description="Méthode de valorisation"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer la valorisation du stock par produit"""
        with get_session() as session:
            products = session.query(Product).filter(Product.is_active == True).all()
            
            valuations = []
            for p in products:
                stock = p.stock or 0
                if stock > 0:
                    purchase_price = p.purchase_price or (p.price * 0.7 if p.price else 0)
                    valuations.append({
                        "product_id": str(p.id),
                        "product_name": p.name,
                        "current_stock": stock,
                        "unit_cost": purchase_price,
                        "total_value": stock * purchase_price,
                        "method": method
                    })
            
            return valuations

