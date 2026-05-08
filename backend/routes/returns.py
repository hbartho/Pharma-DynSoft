"""
Routes Returns - PostgreSQL Implementation
Gère les retours de ventes
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os

from auth import get_current_user, require_open_shift
from models.returns import SaleReturn, SaleReturnCreate

router = APIRouter(prefix="/returns", tags=["Returns"])

DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import SaleReturn as SaleReturnModel, Sale, StockMovement, Product
    from database.models_tenant import StockMovementType, ReturnStatus
    from database.repositories_extended import SaleRepository
    from sqlalchemy import desc, text
    from sqlalchemy.orm import joinedload
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def generate_return_number() -> str:
        """Générer un numéro de retour unique"""
        unique_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
        return f"RET-{unique_id}"
    
    def get_return_delay_days() -> int:
        """Récupérer le délai de retour configuré"""
        with get_session() as session:
            result = session.execute(
                text("SELECT value FROM public.settings WHERE key = 'return_delay_days'")
            ).fetchone()
            if result and result[0]:
                return int(result[0]) if isinstance(result[0], (int, str)) else 3
            return 3  # 3 jours par défaut
    
    def check_sale_return_eligibility(sale_created_at) -> tuple:
        """Vérifier si une vente est éligible au retour"""
        return_delay_days = get_return_delay_days()
        
        sale_date = sale_created_at
        if isinstance(sale_date, str):
            sale_date = datetime.fromisoformat(sale_date.replace('Z', '+00:00'))
        
        deadline = sale_date + timedelta(days=return_delay_days)
        now = datetime.now(timezone.utc)
        
        if now > deadline:
            days_elapsed = (now - sale_date).days
            return (False, f"Le délai de retour de {return_delay_days} jour(s) est dépassé. Cette vente date de {days_elapsed} jour(s).", 0)
        
        days_remaining = (deadline - now).days
        return (True, f"{days_remaining} jour(s) restant(s) pour le retour", days_remaining)
    
    def return_to_dict(r) -> dict:
        """Convertir un retour en dictionnaire"""
        # Le status peut être un enum ou une chaîne
        status_value = r.status.value if hasattr(r.status, 'value') else (r.status or "completed")
        return {
            "id": str(r.id),
            "return_number": r.return_number,
            "sale_id": str(r.sale_id) if r.sale_id else None,
            "total_refund": r.total_refund,
            "reason": r.reason,
            "status": status_value,
            "items": r.items or [],
            "agent_code": r.agent_code,
            "agent_name": r.agent_name,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "tenant_id": "pharmacie_centrale"
        }
    
    # ============== ROUTES ==============
    
    @router.post("", response_model=dict)
    async def create_return(
        return_data: SaleReturnCreate,
        current_user: dict = Depends(require_open_shift)
    ):
        """Créer un retour d'articles pour une vente"""
        employee_code = current_user.get('employee_code', 'N/A')
        employee_name = current_user.get('name', 'Inconnu')
        
        # Vérifier que le motif est fourni
        if not return_data.reason or not return_data.reason.strip():
            raise HTTPException(status_code=400, detail="Le motif du retour est obligatoire")
        
        with get_session() as session:
            # Vérifier que la vente existe
            sale = session.query(Sale).filter(Sale.id == uuid.UUID(return_data.sale_id)).first()
            if not sale:
                raise HTTPException(status_code=404, detail="Vente non trouvée")
            
            # Vérifier le délai de retour
            is_eligible, message, _ = check_sale_return_eligibility(sale.created_at)
            if not is_eligible:
                raise HTTPException(status_code=400, detail=message)
            
            # Valider les items de retour
            sale_items = {str(item.id): item for item in (sale.items or [])}
            return_items = []
            total_refund = 0
            
            for item in return_data.items:
                # Extraire les données de l'item (c'est un dict)
                item_product_id = item.get('product_id') if isinstance(item, dict) else item.product_id
                item_quantity = item.get('quantity') if isinstance(item, dict) else item.quantity
                item_reason = item.get('reason') if isinstance(item, dict) else getattr(item, 'reason', None)
                
                # Trouver l'item correspondant dans la vente
                original_item = None
                for si in (sale.items or []):
                    if str(si.product_id) == item_product_id:
                        original_item = si
                        break
                
                if not original_item:
                    raise HTTPException(status_code=400, detail=f"Produit {item_product_id} non trouvé dans cette vente")
                
                if item_quantity > original_item.quantity:
                    raise HTTPException(status_code=400, detail=f"Quantité de retour supérieure à la quantité vendue pour {original_item.product_name}")
                
                item_refund = original_item.unit_price * item_quantity
                total_refund += item_refund
                
                return_items.append({
                    "product_id": item_product_id,
                    "product_name": original_item.product_name,
                    "quantity": item_quantity,
                    "unit_price": original_item.unit_price,
                    "refund_amount": item_refund,
                    "reason": item_reason or return_data.reason
                })
                
                # Mettre à jour le stock
                product = session.query(Product).filter(Product.id == uuid.UUID(item_product_id)).first()
                if product:
                    product.stock = (product.stock or 0) + item_quantity
                    
                    # Créer un mouvement de stock
                    movement = StockMovement(
                        product_id=product.id,
                        movement_type=StockMovementType.RETURN,
                        quantity=item_quantity,
                        stock_after=product.stock,
                        reference_type="return",
                        agent_code=employee_code,
                        reason=f"Retour vente - {return_data.reason}"
                    )
                    session.add(movement)
            
            # Créer le retour
            return_number = generate_return_number()
            new_return = SaleReturnModel(
                return_number=return_number,
                sale_id=sale.id,
                total_refund=total_refund,
                reason=return_data.reason,
                status="completed",
                items=return_items,
                agent_code=employee_code,
                agent_name=employee_name
            )
            session.add(new_return)
            session.commit()
            session.refresh(new_return)
            
            result = return_to_dict(new_return)
            result["sale_number"] = sale.sale_number
            return result
    
    @router.get("", response_model=List[dict])
    async def get_returns(
        sale_id: Optional[str] = None,
        limit: int = 100,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer tous les retours"""
        with get_session() as session:
            query = session.query(SaleReturnModel)
            
            if sale_id:
                try:
                    query = query.filter(SaleReturnModel.sale_id == uuid.UUID(sale_id))
                except ValueError:
                    pass
            
            returns = query.order_by(desc(SaleReturnModel.created_at)).limit(limit).all()
            return [return_to_dict(r) for r in returns]
    
    @router.get("/history", response_model=List[dict])
    async def get_returns_history(
        limit: int = 50,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des retours"""
        with get_session() as session:
            returns = session.query(SaleReturnModel).order_by(desc(SaleReturnModel.created_at)).limit(limit).all()
            return [return_to_dict(r) for r in returns]
    
    @router.get("/check-eligibility/{sale_id}", response_model=dict)
    async def check_eligibility_alt(
        sale_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Vérifier l'éligibilité d'une vente au retour (route alternative)"""
        with get_session() as session:
            sale = session.query(Sale).filter(Sale.id == uuid.UUID(sale_id)).first()
            if not sale:
                raise HTTPException(status_code=404, detail="Vente non trouvée")
            
            is_eligible, message, days_remaining = check_sale_return_eligibility(sale.created_at)
            
            return {
                "sale_id": sale_id,
                "is_eligible": is_eligible,
                "message": message,
                "days_remaining": days_remaining,
                "return_delay_days": get_return_delay_days()
            }
    
    @router.get("/sale/{sale_id}", response_model=List[dict])
    async def get_returns_by_sale(
        sale_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer les retours pour une vente spécifique"""
        with get_session() as session:
            try:
                returns = session.query(SaleReturnModel).filter(
                    SaleReturnModel.sale_id == uuid.UUID(sale_id)
                ).order_by(desc(SaleReturnModel.created_at)).all()
                return [return_to_dict(r) for r in returns]
            except ValueError:
                return []
    
    @router.get("/sale/{sale_id}/eligibility", response_model=dict)
    async def check_eligibility(
        sale_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Vérifier l'éligibilité d'une vente au retour"""
        with get_session() as session:
            sale = session.query(Sale).filter(Sale.id == uuid.UUID(sale_id)).first()
            if not sale:
                raise HTTPException(status_code=404, detail="Vente non trouvée")
            
            is_eligible, message, days_remaining = check_sale_return_eligibility(sale.created_at)
            
            return {
                "sale_id": sale_id,
                "is_eligible": is_eligible,
                "message": message,
                "days_remaining": days_remaining,
                "return_delay_days": get_return_delay_days()
            }
    
    from fastapi import Query
    
    @router.get("/history/paginated")
    async def get_operations_history_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        type_filter: Optional[str] = Query(default=None, description="all, sale, return"),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des opérations (ventes + retours) avec pagination optimisée"""
        from sqlalchemy.orm import joinedload
        
        with get_session() as session:
            operations = []
            offset = (page - 1) * limit
            
            # Pour le mode "all", on doit calculer le total et charger intelligemment
            # On utilise une limite basée sur la page demandée
            max_items_to_fetch = (page + 2) * limit  # Charger un peu plus pour permettre le scroll
            
            # Requête optimisée pour les ventes avec eager loading
            if type_filter in [None, 'all', 'sale']:
                sales_query = session.query(Sale).options(
                    joinedload(Sale.customer)
                ).filter(
                    Sale.status == 'completed'
                ).order_by(desc(Sale.created_at))
                
                if type_filter == 'sale':
                    total_sales = sales_query.count()
                    sales = sales_query.offset(offset).limit(limit).all()
                    
                    for sale in sales:
                        customer_name = sale.customer.name if sale.customer else 'Client anonyme'
                        operations.append({
                            "id": str(sale.id),
                            "type": "sale",
                            "operation_number": sale.sale_number,
                            "amount": sale.total or 0,
                            "items_count": len(sale.items or []),
                            "employee_code": sale.agent_code,
                            "user_name": sale.agent_name,
                            "user_role": None,
                            "customer_name": customer_name,
                            "payment_method": sale.payment_method.value if sale.payment_method else None,
                            "date": sale.created_at.isoformat() if sale.created_at else None,
                            "created_at": sale.created_at.isoformat() if sale.created_at else None,
                            "details": None
                        })
                    
                    return {
                        "items": operations,
                        "total": total_sales,
                        "page": page,
                        "limit": limit,
                        "pages": (total_sales + limit - 1) // limit if total_sales > 0 else 1,
                        "has_next": page < ((total_sales + limit - 1) // limit),
                        "has_prev": page > 1
                    }
                else:
                    # Mode "all": limiter les ventes chargées
                    sales = sales_query.limit(max_items_to_fetch).all()
                    for sale in sales:
                        customer_name = sale.customer.name if sale.customer else 'Client anonyme'
                        operations.append({
                            "id": str(sale.id),
                            "type": "sale",
                            "operation_number": sale.sale_number,
                            "amount": sale.total or 0,
                            "items_count": len(sale.items or []),
                            "employee_code": sale.agent_code,
                            "user_name": sale.agent_name,
                            "user_role": None,
                            "customer_name": customer_name,
                            "payment_method": sale.payment_method.value if sale.payment_method else None,
                            "date": sale.created_at.isoformat() if sale.created_at else None,
                            "created_at": sale.created_at.isoformat() if sale.created_at else None,
                            "details": None
                        })
            
            # Requête optimisée pour les retours
            if type_filter in [None, 'all', 'return']:
                returns_query = session.query(SaleReturnModel).order_by(desc(SaleReturnModel.created_at))
                
                if type_filter == 'return':
                    total_returns = returns_query.count()
                    returns = returns_query.offset(offset).limit(limit).all()
                    
                    for r in returns:
                        sale = session.query(Sale).filter(Sale.id == r.sale_id).first()
                        operations.append({
                            "id": str(r.id),
                            "type": "return",
                            "operation_number": r.return_number,
                            "amount": r.total_refund,
                            "items_count": len(r.items or []),
                            "employee_code": r.agent_code,
                            "user_name": r.agent_name,
                            "user_role": None,
                            "reason": r.reason,
                            "sale_number": sale.sale_number if sale else None,
                            "date": r.created_at.isoformat() if r.created_at else None,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                            "details": {
                                "id": str(r.id),
                                "return_number": r.return_number,
                                "sale_id": str(r.sale_id) if r.sale_id else None,
                                "sale_number": sale.sale_number if sale else None,
                                "total_refund": r.total_refund,
                                "reason": r.reason,
                                "items": r.items or [],
                                "agent_code": r.agent_code,
                                "agent_name": r.agent_name,
                                "employee_code": r.agent_code,
                                "created_at": r.created_at.isoformat() if r.created_at else None
                            }
                        })
                    
                    return {
                        "items": operations,
                        "total": total_returns,
                        "page": page,
                        "limit": limit,
                        "pages": (total_returns + limit - 1) // limit if total_returns > 0 else 1,
                        "has_next": page < ((total_returns + limit - 1) // limit),
                        "has_prev": page > 1
                    }
                else:
                    # Mode "all": limiter les retours chargés
                    returns = returns_query.limit(max_items_to_fetch).all()
                    # Pré-charger les ventes associées
                    sale_ids = [r.sale_id for r in returns if r.sale_id]
                    sales_map = {}
                    if sale_ids:
                        related_sales = session.query(Sale).filter(Sale.id.in_(sale_ids)).all()
                        sales_map = {s.id: s for s in related_sales}
                    
                    for r in returns:
                        sale = sales_map.get(r.sale_id)
                        operations.append({
                            "id": str(r.id),
                            "type": "return",
                            "operation_number": r.return_number,
                            "amount": r.total_refund,
                            "items_count": len(r.items or []),
                            "employee_code": r.agent_code,
                            "user_name": r.agent_name,
                            "user_role": None,
                            "reason": r.reason,
                            "sale_number": sale.sale_number if sale else None,
                            "date": r.created_at.isoformat() if r.created_at else None,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                            "details": {
                                "id": str(r.id),
                                "return_number": r.return_number,
                                "sale_id": str(r.sale_id) if r.sale_id else None,
                                "sale_number": sale.sale_number if sale else None,
                                "total_refund": r.total_refund,
                                "reason": r.reason,
                                "items": r.items or [],
                                "agent_code": r.agent_code,
                                "agent_name": r.agent_name,
                                "employee_code": r.agent_code,
                                "created_at": r.created_at.isoformat() if r.created_at else None
                            }
                        })
            
            # Trier par date décroissante (pour le mode "all")
            operations.sort(key=lambda x: x.get('created_at') or '', reverse=True)
            
            # Calculer le total approximatif (basé sur les éléments chargés)
            total = len(operations)
            
            # Pagination
            paginated_operations = operations[offset:offset + limit]
            
            # Calculer le nombre de pages basé sur les éléments disponibles
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": paginated_operations,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": len(paginated_operations) == limit,
                "has_prev": page > 1
            }
    
    @router.get("/history/operations", response_model=List[dict])
    async def get_operations_history(
        limit: int = 50,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des opérations (ventes + retours)"""
        with get_session() as session:
            # Récupérer les retours
            returns = session.query(SaleReturnModel).order_by(desc(SaleReturnModel.created_at)).limit(limit).all()
            
            operations = []
            for r in returns:
                operations.append({
                    "id": str(r.id),
                    "type": "return",
                    "reference": r.return_number,
                    "amount": r.total_refund,
                    "items_count": len(r.items or []),
                    "agent_code": r.agent_code,
                    "agent_name": r.agent_name,
                    "reason": r.reason,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                })
            
            return operations
    
    # Route avec paramètre dynamique - doit être à la fin pour éviter les conflits
    @router.get("/{return_id}", response_model=dict)
    async def get_return(
        return_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer un retour par ID"""
        with get_session() as session:
            try:
                ret = session.query(SaleReturnModel).filter(SaleReturnModel.id == uuid.UUID(return_id)).first()
            except ValueError:
                ret = session.query(SaleReturnModel).filter(SaleReturnModel.return_number == return_id).first()
            
            if not ret:
                raise HTTPException(status_code=404, detail="Retour non trouvé")
            
            return return_to_dict(ret)
