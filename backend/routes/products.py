"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from auth import require_role, get_current_user
from models.product import Product, ProductCreate, ProductUpdate, ProductWithStock
import os

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/products", tags=["Products"])

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories import ProductRepository, SettingsRepository, CategoryRepository
    from database.config import db_manager, USE_SUPABASE
    from database.models_tenant import Product as ProductModel
    from sqlalchemy import desc, or_
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    def get_expiration_alert_days() -> int:
        """Récupérer le délai d'alerte de péremption"""
        settings_repo = SettingsRepository()
        return settings_repo.get("expiration_alert_days", 30)
    
    @router.get("/paginated")
    async def get_products_paginated(
        page: int = Query(default=1, ge=1),
        limit: int = Query(default=20, ge=1, le=100),
        search: str = Query(default=""),
        category_id: Optional[str] = Query(default=None),
        status: Optional[str] = Query(default=None, description="all, active, inactive"),
        sort_by: Optional[str] = Query(default="priority", description="priority, name, stock, expiration"),
        current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))
    ):
        """Récupérer les produits avec pagination serveur pour infinite scroll"""
        import uuid
        
        with get_session() as session:
            # Base query
            query = session.query(ProductModel)
            
            # Filtre par recherche (nom ou code-barres)
            if search:
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        ProductModel.name.ilike(search_term),
                        ProductModel.barcode.ilike(search_term),
                        ProductModel.internal_reference.ilike(search_term)
                    )
                )
            
            # Filtre par catégorie
            if category_id and category_id != 'all':
                try:
                    query = query.filter(ProductModel.category_id == uuid.UUID(category_id))
                except ValueError:
                    pass
            
            # Filtre par statut
            if status == 'active':
                query = query.filter(ProductModel.is_active == True)
            elif status == 'inactive':
                query = query.filter(ProductModel.is_active == False)
            elif status == 'low_stock':
                # Récupérer le seuil de stock bas depuis les paramètres
                from database.repositories import SettingsRepository
                settings_repo = SettingsRepository()
                settings = settings_repo.get_all()
                low_stock_threshold = settings.get('low_stock_threshold', 10)
                query = query.filter(
                    ProductModel.is_active == True,
                    ProductModel.stock <= low_stock_threshold
                )
            elif status == 'out_of_stock':
                query = query.filter(
                    ProductModel.is_active == True,
                    ProductModel.stock <= 0
                )
            elif status == 'near_expiration':
                # Produits dont la date d'expiration est proche (dans les X jours)
                from database.repositories import SettingsRepository
                settings_repo = SettingsRepository()
                settings = settings_repo.get_all()
                expiration_alert_days = settings.get('expiration_alert_days', 30)
                today = datetime.now(timezone.utc).date()
                expiration_threshold = today + timedelta(days=expiration_alert_days)
                query = query.filter(
                    ProductModel.is_active == True,
                    ProductModel.expiration_date != None,
                    ProductModel.expiration_date <= expiration_threshold,
                    ProductModel.expiration_date > today  # Pas encore périmé
                )
            elif status == 'expired':
                # Produits périmés (date d'expiration passée)
                today = datetime.now(timezone.utc).date()
                query = query.filter(
                    ProductModel.expiration_date != None,
                    ProductModel.expiration_date < today
                )
            
            # Compter le total
            total = query.count()
            
            # Appliquer tri - par défaut nom pour une pagination simple
            query = query.order_by(ProductModel.name.asc())
            
            # Pagination
            offset = (page - 1) * limit
            products_orm = query.offset(offset).limit(limit).all()
            
            # Convertir en dictionnaires et enrichir
            now = datetime.now(timezone.utc)
            expiration_alert_days = get_expiration_alert_days()
            expiration_threshold = now + timedelta(days=expiration_alert_days)
            
            # Charger les catégories pour enrichir
            cat_repo = CategoryRepository()
            categories = {str(c['id']): c for c in cat_repo.get_all()}
            
            products = []
            for p in products_orm:
                product = {
                    "id": str(p.id),
                    "name": p.name,
                    "internal_reference": p.internal_reference,
                    "barcode": p.barcode,
                    "description": p.description,
                    "category_id": str(p.category_id) if p.category_id else None,
                    "unit_id": str(p.unit_id) if p.unit_id else None,
                    "purchase_price": float(p.purchase_price or 0),
                    "price": float(p.price or 0),
                    "stock": p.stock or 0,
                    "min_stock": p.min_stock or 10,
                    "is_active": p.is_active if p.is_active is not None else True,
                    "expiration_date": p.expiration_date.isoformat() if p.expiration_date else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                
                # Ajouter infos catégorie
                if product['category_id'] and product['category_id'] in categories:
                    cat = categories[product['category_id']]
                    product['category_name'] = cat.get('name')
                    product['markup_coefficient'] = cat.get('markup_coefficient', 1.0)
                
                # Calculer alertes
                product['needs_restock'] = product['stock'] <= product['min_stock']
                
                if product['expiration_date']:
                    try:
                        exp_date = datetime.fromisoformat(product['expiration_date'].replace('Z', '+00:00'))
                        if exp_date.tzinfo is None:
                            exp_date = exp_date.replace(tzinfo=timezone.utc)
                        product['near_expiration'] = exp_date <= expiration_threshold
                        product['days_until_expiration'] = (exp_date - now).days
                    except:
                        product['near_expiration'] = False
                        product['days_until_expiration'] = 9999
                else:
                    product['near_expiration'] = False
                    product['days_until_expiration'] = 9999
                
                products.append(product)
            
            # Calculer pages
            pages = (total + limit - 1) // limit if total > 0 else 1
            
            return {
                "items": products,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
                "has_next": page < pages,
                "has_prev": page > 1
            }
    
    @router.post("")
    async def create_product(product_data: ProductCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Créer un nouveau produit"""
        repo = ProductRepository()
        
        # Vérifier si un produit avec le même nom existe
        existing = repo.get_by_name(product_data.name)
        if existing:
            raise HTTPException(status_code=400, detail=f"Un produit avec le nom '{product_data.name}' existe déjà")
        
        # Vérifier code-barres
        if product_data.barcode:
            existing_barcode = repo.get_by_barcode(product_data.barcode)
            if existing_barcode:
                raise HTTPException(status_code=400, detail=f"Un produit avec le code-barres '{product_data.barcode}' existe déjà")
        
        data = product_data.model_dump()
        result = repo.create(data)
        return result
    
    @router.get("")
    async def get_products(
        sort_by: Optional[str] = Query(default="priority", description="priority, name, stock, expiration"),
        current_user: dict = Depends(require_role(["admin", "pharmacien", "caissier"]))
    ):
        """Récupérer tous les produits avec tri par priorité"""
        repo = ProductRepository()
        expiration_alert_days = get_expiration_alert_days()
        
        products = repo.get_all()
        now = datetime.now(timezone.utc)
        expiration_threshold = now + timedelta(days=expiration_alert_days)
        
        # Ajouter indicateurs de tri
        for product in products:
            product['_needs_restock'] = product.get('stock', 0) <= product.get('min_stock', 10)
            
            exp_date_str = product.get('expiration_date')
            if exp_date_str:
                try:
                    exp_date = datetime.fromisoformat(exp_date_str.replace('Z', '+00:00')) if isinstance(exp_date_str, str) else exp_date_str
                    if exp_date.tzinfo is None:
                        exp_date = exp_date.replace(tzinfo=timezone.utc)
                    product['_near_expiration'] = exp_date <= expiration_threshold
                    product['_days_until_expiration'] = (exp_date - now).days
                except:
                    product['_near_expiration'] = False
                    product['_days_until_expiration'] = 9999
            else:
                product['_near_expiration'] = False
                product['_days_until_expiration'] = 9999
        
        # Tri par priorité
        def sort_key(p):
            needs_restock = 0 if p.get('_needs_restock') else 1
            near_expiration = 0 if p.get('_near_expiration') else 1
            days = p.get('_days_until_expiration', 9999)
            name = p.get('name', '').lower()
            return (needs_restock, near_expiration, days, name)
        
        products.sort(key=sort_key)
        
        # Nettoyer champs temporaires
        for product in products:
            product.pop('_needs_restock', None)
            product.pop('_near_expiration', None)
            product.pop('_days_until_expiration', None)
        
        return products
    
    @router.get("/alerts")
    async def get_product_alerts(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Récupérer les alertes: stock bas et péremption proche"""
        repo = ProductRepository()
        settings_repo = SettingsRepository()
        
        low_stock_threshold = settings_repo.get("low_stock_threshold", 10)
        expiration_alert_days = settings_repo.get("expiration_alert_days", 30)
        
        low_stock_products = repo.get_low_stock()
        near_expiration_products = repo.get_expiring_soon(expiration_alert_days)
        
        now = datetime.now(timezone.utc)
        expired_products = []
        near_exp = []
        
        for p in near_expiration_products:
            exp_str = p.get('expiration_date')
            if exp_str:
                try:
                    exp_date = datetime.fromisoformat(exp_str.replace('Z', '+00:00')) if isinstance(exp_str, str) else exp_str
                    if exp_date <= now:
                        expired_products.append({"id": p['id'], "name": p['name'], "expiration_date": exp_str})
                    else:
                        near_exp.append({"id": p['id'], "name": p['name'], "expiration_date": exp_str, "days_until_expiration": (exp_date - now).days})
                except:
                    pass
        
        return {
            "low_stock": {
                "count": len(low_stock_products),
                "threshold": low_stock_threshold,
                "products": [{"id": p['id'], "name": p['name'], "stock": p['stock'], "min_stock": p['min_stock']} for p in low_stock_products]
            },
            "near_expiration": {
                "count": len(near_exp),
                "alert_days": expiration_alert_days,
                "products": near_exp
            },
            "expired": {
                "count": len(expired_products),
                "products": expired_products
            }
        }
    
    @router.get("/search")
    async def search_products(q: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Rechercher des produits"""
        repo = ProductRepository()
        return repo.search(q, limit=50)
    
    @router.get("/{product_id}")
    async def get_product(product_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
        """Récupérer un produit spécifique"""
        repo = ProductRepository()
        product = repo.get_by_id_str(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        return product
    
    @router.put("/{product_id}")
    async def update_product(
        product_id: str,
        product_data: ProductUpdate,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour un produit"""
        repo = ProductRepository()
        
        existing = repo.get_by_id_str(product_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        # Vérifier nom unique
        if product_data.name:
            existing_name = repo.get_by_name(product_data.name)
            if existing_name and existing_name['id'] != product_id:
                raise HTTPException(status_code=400, detail=f"Un autre produit avec le nom '{product_data.name}' existe déjà")
        
        # Vérifier code-barres unique
        if product_data.barcode:
            existing_barcode = repo.get_by_barcode(product_data.barcode)
            if existing_barcode and existing_barcode['id'] != product_id:
                raise HTTPException(status_code=400, detail=f"Un autre produit avec le code-barres '{product_data.barcode}' existe déjà")
        
        update_data = {k: v for k, v in product_data.model_dump().items() if v is not None}
        result = repo.update_by_id_str(product_id, update_data)
        return result
    
    @router.patch("/{product_id}/toggle-status")
    async def toggle_product_status(product_id: str, current_user: dict = Depends(require_role(["admin"]))):
        """Activer/Désactiver un produit"""
        repo = ProductRepository()
        result = repo.toggle_status_by_id_str(product_id)
        if not result:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        status_text = "activé" if result['is_active'] else "désactivé"
        return {"message": f"Produit {status_text} avec succès", "is_active": result['is_active']}
    
    @router.patch("/{product_id}/min-stock")
    async def update_product_min_stock_endpoint(
        product_id: str,
        min_stock: int,
        current_user: dict = Depends(require_role(["admin", "pharmacien"]))
    ):
        """Mettre à jour le stock minimum"""
        repo = ProductRepository()
        result = repo.update_by_id_str(product_id, {"min_stock": min_stock})
        if not result:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        return {"message": "Stock minimum mis à jour", "min_stock": min_stock}
    
    @router.delete("/{product_id}")
    async def delete_product(product_id: str, current_user: dict = Depends(require_role(["admin"]))):
        """Supprimer un produit"""
        repo = ProductRepository()
        
        product = repo.get_by_id_str(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        # Vérifier si stock > 0
        if product.get('stock', 0) > 0:
            raise HTTPException(status_code=400, detail="Impossible de supprimer ce produit : il a du stock. Vous pouvez le désactiver.")
        
        success = repo.delete_by_id_str(product_id)
        if not success:
            raise HTTPException(status_code=404, detail="Produit non trouvé")
        
        return {"message": "Produit supprimé avec succès"}
