"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import os

from auth import get_current_user
from models.pending_sale import PendingSale, PendingSaleCreate, PendingSaleUpdate

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/pending-sales", tags=["Pending Sales"])

EXPIRATION_HOURS = 24

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import PendingSale as PendingSaleModel, Customer, Product
    from sqlalchemy import desc
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def pending_sale_to_dict(p) -> dict:
        if p is None:
            return None
        now = datetime.now(timezone.utc)
        expires_at = p.expires_at
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            remaining = expires_at - now
            time_remaining = max(0, int(remaining.total_seconds() / 60))
        else:
            time_remaining = 0
        
        return {
            "id": str(p.id),
            "reference": f"ATT-{str(p.id)[:3].upper()}",
            "customer_id": str(p.customer_id) if p.customer_id else None,
            "customer_name": p.customer_name,
            "items": p.cart_items or [],
            "subtotal": p.subtotal,
            "discount_amount": p.discount,
            "discount_type": p.discount_type,
            "discount_value": p.discount_value,
            "total": p.total,
            "notes": p.notes,
            "status": "pending",
            "created_by_name": p.agent_name,
            "created_at": p.created_at,
            "expires_at": p.expires_at,
            "time_remaining_minutes": time_remaining,
            "tenant_id": "pharmacie_centrale",
        }
    
    async def cleanup_expired_pending_sales():
        """Supprimer les ventes en attente expirées"""
        now = datetime.now(timezone.utc)
        with get_session() as session:
            session.query(PendingSaleModel).filter(
                PendingSaleModel.expires_at < now
            ).delete()
            session.commit()
    
    @router.get("")
    async def get_pending_sales(
        status: Optional[str] = "pending",
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer toutes les ventes en attente"""
        await cleanup_expired_pending_sales()
        
        with get_session() as session:
            query = session.query(PendingSaleModel)
            
            # Filtrer les expirées
            now = datetime.now(timezone.utc)
            query = query.filter(PendingSaleModel.expires_at > now)
            
            pending_sales = query.order_by(desc(PendingSaleModel.created_at)).all()
            return [pending_sale_to_dict(p) for p in pending_sales]
    
    @router.get("/count")
    async def get_pending_sales_count(current_user: dict = Depends(get_current_user)):
        """Récupérer le nombre de ventes en attente actives"""
        await cleanup_expired_pending_sales()
        
        with get_session() as session:
            now = datetime.now(timezone.utc)
            count = session.query(PendingSaleModel).filter(
                PendingSaleModel.expires_at > now
            ).count()
            return {"count": count}
    
    @router.get("/{pending_id}")
    async def get_pending_sale(
        pending_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer une vente en attente par son ID"""
        with get_session() as session:
            pending_sale = session.query(PendingSaleModel).filter(
                PendingSaleModel.id == uuid.UUID(pending_id)
            ).first()
            
            if not pending_sale:
                raise HTTPException(status_code=404, detail="Vente en attente non trouvée")
            
            return pending_sale_to_dict(pending_sale)
    
    @router.post("", response_model=dict)
    async def create_pending_sale(
        sale_data: PendingSaleCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Créer une nouvelle vente en attente"""
        employee_code = current_user.get('employee_code', current_user.get('email', 'N/A'))
        
        # Récupérer le nom du client si fourni
        customer_name = None
        if sale_data.customer_id:
            with get_session() as session:
                customer = session.query(Customer).filter(
                    Customer.id == uuid.UUID(sale_data.customer_id)
                ).first()
                if customer:
                    customer_name = customer.name
        
        # Enrichir les items avec les noms des produits
        enriched_items = []
        with get_session() as session:
            for item in sale_data.items:
                product = session.query(Product).filter(
                    Product.id == uuid.UUID(item['product_id'])
                ).first()
                enriched_item = {
                    **item,
                    "product_name": product.name if product else 'Produit inconnu'
                }
                enriched_items.append(enriched_item)
        
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=EXPIRATION_HOURS)
        
        with get_session() as session:
            pending_sale = PendingSaleModel(
                id=uuid.uuid4(),
                customer_id=uuid.UUID(sale_data.customer_id) if sale_data.customer_id else None,
                customer_name=customer_name,
                agent_code=employee_code,
                agent_name=employee_code,
                cart_items=enriched_items,
                subtotal=sale_data.subtotal,
                discount=sale_data.discount_amount or 0,
                discount_type=sale_data.discount_type,
                discount_value=sale_data.discount_value or 0,
                total=sale_data.total,
                notes=sale_data.notes,
                expires_at=expires_at,
                created_at=now
            )
            session.add(pending_sale)
            session.commit()
            
            return {
                "message": "Vente mise en attente",
                "id": str(pending_sale.id),
                "reference": f"ATT-{str(pending_sale.id)[:3].upper()}",
                "expires_at": expires_at.isoformat(),
                "expires_in_hours": EXPIRATION_HOURS
            }
    
    @router.put("/{pending_id}")
    async def update_pending_sale(
        pending_id: str,
        sale_data: PendingSaleUpdate,
        current_user: dict = Depends(get_current_user)
    ):
        """Mettre à jour une vente en attente"""
        with get_session() as session:
            pending_sale = session.query(PendingSaleModel).filter(
                PendingSaleModel.id == uuid.UUID(pending_id)
            ).first()
            
            if not pending_sale:
                raise HTTPException(status_code=404, detail="Vente en attente non trouvée")
            
            if sale_data.customer_id is not None:
                pending_sale.customer_id = uuid.UUID(sale_data.customer_id) if sale_data.customer_id else None
                if sale_data.customer_id:
                    customer = session.query(Customer).filter(
                        Customer.id == uuid.UUID(sale_data.customer_id)
                    ).first()
                    pending_sale.customer_name = customer.name if customer else None
                else:
                    pending_sale.customer_name = None
            
            if sale_data.items is not None:
                enriched_items = []
                for item in sale_data.items:
                    product = session.query(Product).filter(
                        Product.id == uuid.UUID(item['product_id'])
                    ).first()
                    enriched_item = {
                        **item,
                        "product_name": product.name if product else 'Produit inconnu'
                    }
                    enriched_items.append(enriched_item)
                pending_sale.cart_items = enriched_items
            
            if sale_data.subtotal is not None:
                pending_sale.subtotal = sale_data.subtotal
            if sale_data.discount_amount is not None:
                pending_sale.discount = sale_data.discount_amount
            if sale_data.total is not None:
                pending_sale.total = sale_data.total
            if sale_data.notes is not None:
                pending_sale.notes = sale_data.notes
            
            session.commit()
            
            return {"message": "Vente en attente mise à jour", "id": pending_id}
    
    @router.delete("/{pending_id}")
    async def cancel_pending_sale(
        pending_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Annuler une vente en attente"""
        with get_session() as session:
            pending_sale = session.query(PendingSaleModel).filter(
                PendingSaleModel.id == uuid.UUID(pending_id)
            ).first()
            
            if not pending_sale:
                raise HTTPException(status_code=404, detail="Vente en attente non trouvée")
            
            session.delete(pending_sale)
            session.commit()
            
            return {"message": "Vente en attente annulée", "id": pending_id}
    
    @router.post("/{pending_id}/complete")
    async def complete_pending_sale(
        pending_id: str,
        payment_method: str,
        payment_details: dict = None,
        is_split_payment: bool = False,
        split_payments: list = None,
        amount_paid: float = None,
        debt_amount: float = None,
        current_user: dict = Depends(get_current_user)
    ):
        """Finaliser une vente en attente"""
        with get_session() as session:
            pending_sale = session.query(PendingSaleModel).filter(
                PendingSaleModel.id == uuid.UUID(pending_id)
            ).first()
            
            if not pending_sale:
                raise HTTPException(status_code=404, detail="Vente en attente non trouvée")
            
            # Vérifier l'expiration
            now = datetime.now(timezone.utc)
            if pending_sale.expires_at and now > pending_sale.expires_at:
                session.delete(pending_sale)
                session.commit()
                raise HTTPException(status_code=400, detail="Cette vente en attente a expiré")
            
            # Retourner les données pour que le frontend puisse créer la vente
            result = pending_sale_to_dict(pending_sale)
            
            # Supprimer la vente en attente
            session.delete(pending_sale)
            session.commit()
            
            return {
                "message": "Vente prête à être finalisée",
                "pending_sale": result,
                "status": "ready_for_completion"
            }

