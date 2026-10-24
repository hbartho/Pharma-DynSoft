"""
Routes Prices - PostgreSQL Implementation
Gère l'historique des prix
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import os

from auth import require_role, get_current_user
from models.price import PriceHistory, PriceHistoryCreate, PriceChangeType, PriceSummary

router = APIRouter(prefix="/prices", tags=["Prices"])

DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")
from database.tenant_context import get_current_tenant
from services.pricing import estimate_purchase_price


if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Product
    from database.repositories import ProductRepository
    from sqlalchemy import desc, text
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session(get_current_tenant())
        return db_manager.get_tenant_session(get_current_tenant())
    
    # Stockage en mémoire de l'historique des prix (simplifié)
    # Dans une vraie implémentation, créer une table price_history
    from database.models_tenant import PriceHistory as PriceHistoryModel
    from services.price_history import record_price_change, price_history_to_dict
    from sqlalchemy import func as sa_func

    def create_price_history(
        product_id: str,
        prix_appro: float,
        prix_vente_prod: float,
        change_type: PriceChangeType,
        employee_code: str,
        date_appro: datetime = None,
        date_peremption: datetime = None,
        reference_type: str = None,
        reference_id: str = None,
        notes: str = None
    ) -> dict:
        """Met à jour les prix du produit et enregistre l'historique (même transaction)."""
        with get_session() as session:
            try:
                product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).with_for_update().first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            if not product:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            
            entry = record_price_change(
                session, product, prix_appro, prix_vente_prod,
                change_type.value if hasattr(change_type, "value") else str(change_type),
                employee_code, reference_type=reference_type, reference_id=reference_id, notes=notes,
            )
            product.purchase_price = prix_appro
            product.price = prix_vente_prod
            session.flush()
            if entry is None:
                return {"message": "Aucun changement de prix", "product_id": product_id}
            return price_history_to_dict(entry)

    def _history_query(session, product_id=None, change_type=None, search=None):
        q = session.query(PriceHistoryModel)
        if product_id:
            try:
                q = q.filter(PriceHistoryModel.product_id == uuid.UUID(product_id))
            except ValueError:
                pass
        if change_type and change_type != 'all':
            q = q.filter(PriceHistoryModel.change_type == change_type)
        if search:
            q = q.filter(PriceHistoryModel.product_name.ilike(f"%{search}%"))
        return q

    @router.get("/history/paginated")
    def get_price_history_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        change_type: Optional[str] = Query(default=None),
        product_id: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des prix avec pagination pour infinite scroll"""
        with get_session() as session:
            q = _history_query(session, product_id, change_type, search)
            total = q.count()
            pages = (total + limit - 1) // limit if total > 0 else 1
            items = q.order_by(desc(PriceHistoryModel.created_at)).offset((page - 1) * limit).limit(limit).all()
            return {
                "items": [price_history_to_dict(h) for h in items],
                "total": total, "page": page, "limit": limit, "pages": pages,
                "has_next": page < pages, "has_prev": page > 1,
            }
    
    @router.get("/history", response_model=List[dict])
    def get_price_history(
        product_id: Optional[str] = None,
        change_type: Optional[str] = None,
        limit: int = Query(default=100, le=500),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des prix"""
        with get_session() as session:
            items = _history_query(session, product_id, change_type).order_by(desc(PriceHistoryModel.created_at)).limit(limit).all()
            return [price_history_to_dict(h) for h in items]
    
    @router.get("/history/{history_id}", response_model=dict)
    def get_price_history_entry(
        history_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer une entrée d'historique par ID"""
        with get_session() as session:
            try:
                h = session.query(PriceHistoryModel).filter(PriceHistoryModel.id == uuid.UUID(history_id)).first()
            except ValueError:
                h = None
            if not h:
                raise HTTPException(status_code=404, detail="Entrée non trouvée")
            return price_history_to_dict(h)
    
    @router.post("/update", response_model=dict)
    def update_product_prices(
        data: PriceHistoryCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Mettre à jour les prix d'un produit"""
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        employee_code = current_user.get("employee_code", "N/A")
        
        entry = create_price_history(
            product_id=data.product_id,
            prix_appro=data.prix_appro,
            prix_vente_prod=data.prix_vente_prod,
            change_type=data.change_type,
            employee_code=employee_code,
            notes=data.notes
        )
        
        return entry
    
    @router.get("/summary", response_model=dict)
    def get_prices_summary(
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer un résumé des prix"""
        with get_session() as session:
            products = session.query(Product).filter(Product.is_active == True).all()
            
            total_products = len(products)
            total_stock_value = 0
            avg_margin = 0
            margins = []
            
            for p in products:
                stock = p.stock or 0
                price = p.price or 0
                purchase_price = estimate_purchase_price(price, p.purchase_price)
                
                total_stock_value += stock * price
                
                if purchase_price > 0:
                    margin = ((price - purchase_price) / purchase_price) * 100
                    margins.append(margin)
            
            if margins:
                avg_margin = sum(margins) / len(margins)
            
            return {
                "total_products": total_products,
                "total_stock_value": total_stock_value,
                "average_margin_percent": round(avg_margin, 2),
                "price_updates_today": session.query(sa_func.count(PriceHistoryModel.id)).filter(sa_func.date(PriceHistoryModel.created_at) == datetime.now(timezone.utc).date()).scalar() or 0
            }

