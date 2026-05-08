"""
Routes Sync - PostgreSQL Implementation
Synchronisation pour le mode offline (PWA)
"""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timezone
import os

from auth import get_current_user
from models.sync import SyncData

router = APIRouter(prefix="/sync", tags=["Synchronization"])

DATABASE_TYPE = os.environ.get("DB_TYPE", "postgresql")

if DATABASE_TYPE == "postgresql":
    from database.config import db_manager, USE_SUPABASE
    from database.repositories import ProductRepository, CustomerRepository
    from database.repositories_extended import SaleRepository
    
    def get_session():
        if USE_SUPABASE:
            return db_manager.get_tenant_session("default")
        return db_manager.get_tenant_session("pharmacie_centrale")
    
    @router.post("/push")
    async def sync_push(sync_data: SyncData, current_user: dict = Depends(get_current_user)):
        """Push changes to server (PostgreSQL)"""
        from database.models_tenant import Product, Customer, Sale
        import uuid
        
        synced_count = 0
        
        with get_session() as session:
            for change in sync_data.changes:
                try:
                    payload = change.get('payload', {})
                    action = change.get('action')
                    change_type = change.get('type')
                    
                    if change_type == 'product':
                        if action == 'create':
                            product = Product(
                                id=uuid.UUID(payload.get('id', str(uuid.uuid4()))),
                                name=payload.get('name'),
                                price=payload.get('price', 0),
                                stock=payload.get('stock', 0),
                                description=payload.get('description')
                            )
                            session.merge(product)
                        elif action == 'update':
                            product = session.query(Product).filter(Product.id == uuid.UUID(payload['id'])).first()
                            if product:
                                for key, value in payload.items():
                                    if key != 'id' and hasattr(product, key):
                                        setattr(product, key, value)
                        elif action == 'delete':
                            product = session.query(Product).filter(Product.id == uuid.UUID(payload['id'])).first()
                            if product:
                                product.is_active = False
                    
                    elif change_type == 'customer':
                        if action == 'create':
                            customer = Customer(
                                id=uuid.UUID(payload.get('id', str(uuid.uuid4()))),
                                name=payload.get('name'),
                                phone=payload.get('phone'),
                                email=payload.get('email')
                            )
                            session.merge(customer)
                        elif action == 'update':
                            customer = session.query(Customer).filter(Customer.id == uuid.UUID(payload['id'])).first()
                            if customer:
                                for key, value in payload.items():
                                    if key != 'id' and hasattr(customer, key):
                                        setattr(customer, key, value)
                    
                    elif change_type == 'sale':
                        if action == 'create':
                            # Les ventes sont plus complexes, utiliser le repository
                            sale_repo = SaleRepository()
                            sale_repo.create(payload)
                    
                    synced_count += 1
                
                except Exception as e:
                    print(f"Sync error for {change}: {e}")
                    continue
            
            session.commit()
        
        return {"message": f"Synced {synced_count} changes"}
    
    @router.get("/pull")
    async def sync_pull(since: Optional[str] = None, current_user: dict = Depends(get_current_user)):
        """Pull changes from server (PostgreSQL)"""
        product_repo = ProductRepository()
        customer_repo = CustomerRepository()
        sale_repo = SaleRepository()
        
        # Récupérer les données
        products = product_repo.get_all()
        customers = customer_repo.get_all()
        sales = sale_repo.get_all(limit=100)
        
        # Filtrer par date si spécifié
        if since:
            try:
                since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
                products = [p for p in products if p.get('updated_at') and datetime.fromisoformat(p['updated_at'].replace('Z', '+00:00')) > since_date]
                customers = [c for c in customers if c.get('updated_at') and datetime.fromisoformat(c['updated_at'].replace('Z', '+00:00')) > since_date]
                sales = [s for s in sales if s.get('updated_at') and datetime.fromisoformat(s['updated_at'].replace('Z', '+00:00')) > since_date]
            except:
                pass
        
        return {
            "products": products,
            "customers": customers,
            "sales": sales,
            "synced_at": datetime.now(timezone.utc).isoformat()
        }
    
    @router.get("/status")
    async def sync_status(current_user: dict = Depends(get_current_user)):
        """Vérifier le statut de synchronisation"""
        product_repo = ProductRepository()
        customer_repo = CustomerRepository()
        sale_repo = SaleRepository()
        
        return {
            "status": "connected",
            "database": "postgresql",
            "counts": {
                "products": len(product_repo.get_all()),
                "customers": len(customer_repo.get_all()),
                "sales": sale_repo.count_all() if hasattr(sale_repo, 'count_all') else 0
            },
            "last_sync": datetime.now(timezone.utc).isoformat()
        }

