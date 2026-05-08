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

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Product
    from database.repositories import ProductRepository
    from sqlalchemy import desc, text
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    # Stockage en mémoire de l'historique des prix (simplifié)
    # Dans une vraie implémentation, créer une table price_history
    _price_history = []
    
    async def create_price_history(
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
        """Créer une entrée d'historique de prix"""
        with get_session() as session:
            try:
                product = session.query(Product).filter(Product.id == uuid.UUID(product_id)).first()
            except ValueError:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            
            if not product:
                raise HTTPException(status_code=404, detail="Produit non trouvé")
            
            prix_appro_avant = product.purchase_price or 0
            prix_vente_avant = product.price or 0
            
            # Créer l'entrée d'historique
            entry = {
                "id": str(uuid.uuid4()),
                "product_id": product_id,
                "product_name": product.name,
                "product_reference": product.internal_reference,
                "prix_appro": prix_appro,
                "prix_vente_prod": prix_vente_prod,
                "prix_appro_avant": prix_appro_avant,
                "prix_vente_avant": prix_vente_avant,
                "date_maj_prix": datetime.now(timezone.utc).isoformat(),
                "date_appro": date_appro.isoformat() if date_appro else None,
                "date_peremption": date_peremption.isoformat() if date_peremption else None,
                "change_type": change_type.value,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "notes": notes,
                "created_by": employee_code,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            _price_history.insert(0, entry)
            
            # Mettre à jour le produit
            product.purchase_price = prix_appro
            product.price = prix_vente_prod
            session.commit()
            
            return entry
    
    @router.get("/history/paginated")
    async def get_price_history_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        change_type: Optional[str] = Query(default=None),
        product_id: Optional[str] = Query(default=None),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des prix avec pagination pour infinite scroll"""
        result = _price_history.copy()
        
        if product_id:
            result = [h for h in result if h.get("product_id") == product_id]
        
        if change_type and change_type != 'all':
            result = [h for h in result if h.get("change_type") == change_type]
        
        if search:
            search_lower = search.lower()
            result = [h for h in result if search_lower in (h.get("product_name", "") or "").lower()]
        
        total = len(result)
        pages = (total + limit - 1) // limit if total > 0 else 1
        
        offset = (page - 1) * limit
        items = result[offset:offset + limit]
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
    
    @router.get("/history", response_model=List[dict])
    async def get_price_history(
        product_id: Optional[str] = None,
        change_type: Optional[str] = None,
        limit: int = Query(default=100, le=500),
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer l'historique des prix"""
        result = _price_history.copy()
        
        if product_id:
            result = [h for h in result if h.get("product_id") == product_id]
        
        if change_type:
            result = [h for h in result if h.get("change_type") == change_type]
        
        return result[:limit]
    
    @router.get("/history/{history_id}", response_model=dict)
    async def get_price_history_entry(
        history_id: str,
        current_user: dict = Depends(get_current_user)
    ):
        """Récupérer une entrée d'historique par ID"""
        for entry in _price_history:
            if entry.get("id") == history_id:
                return entry
        
        raise HTTPException(status_code=404, detail="Entrée non trouvée")
    
    @router.post("/update", response_model=dict)
    async def update_product_prices(
        data: PriceHistoryCreate,
        current_user: dict = Depends(get_current_user)
    ):
        """Mettre à jour les prix d'un produit"""
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
        
        employee_code = current_user.get("employee_code", "N/A")
        
        entry = await create_price_history(
            product_id=data.product_id,
            prix_appro=data.prix_appro,
            prix_vente_prod=data.prix_vente_prod,
            change_type=data.change_type,
            employee_code=employee_code,
            notes=data.notes
        )
        
        return entry
    
    @router.get("/summary", response_model=dict)
    async def get_prices_summary(
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
                purchase_price = p.purchase_price or (price * 0.7)
                
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
                "price_updates_today": len([h for h in _price_history if h.get("created_at", "")[:10] == datetime.now().strftime("%Y-%m-%d")])
            }

