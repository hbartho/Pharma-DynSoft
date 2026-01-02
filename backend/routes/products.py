from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from database import db
from auth import require_role, get_current_user
from models.product import Product, ProductCreate

router = APIRouter(prefix="/products", tags=["Products"])


async def get_expiration_alert_days(tenant_id: str) -> int:
    """Récupérer le délai d'alerte de péremption configuré"""
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if settings:
        return settings.get("expiration_alert_days", 30)
    return 30


@router.post("", response_model=Product)
async def create_product(product_data: ProductCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Create a new product"""
    # Vérifier si un produit avec le même nom existe déjà
    existing_by_name = await db.products.find_one({
        "tenant_id": current_user['tenant_id'],
        "name": {"$regex": f"^{product_data.name}$", "$options": "i"}
    })
    if existing_by_name:
        raise HTTPException(
            status_code=400,
            detail=f"Un produit avec le nom '{product_data.name}' existe déjà"
        )
    
    # Vérifier si un produit avec le même code-barres existe déjà (si fourni)
    if product_data.barcode:
        existing_by_barcode = await db.products.find_one({
            "tenant_id": current_user['tenant_id'],
            "barcode": product_data.barcode
        })
        if existing_by_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"Un produit avec le code-barres '{product_data.barcode}' existe déjà ({existing_by_barcode['name']})"
            )
    
    product_dict = product_data.model_dump()
    product_dict['tenant_id'] = current_user['tenant_id']
    product_obj = Product(**product_dict)
    
    doc = product_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('expiration_date'):
        doc['expiration_date'] = doc['expiration_date'].isoformat()
    
    await db.products.insert_one(doc)
    return product_obj


@router.get("", response_model=List[Product])
async def get_products(
    sort_by: Optional[str] = Query(default="priority", description="priority, name, stock, expiration"),
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Get all products sorted by priority: low stock > near expiration > alphabetical"""
    tenant_id = current_user['tenant_id']
    products = await db.products.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    
    # Récupérer le délai d'alerte de péremption
    expiration_alert_days = await get_expiration_alert_days(tenant_id)
    expiration_threshold = datetime.now(timezone.utc) + timedelta(days=expiration_alert_days)
    
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
        if isinstance(product.get('updated_at'), str):
            product['updated_at'] = datetime.fromisoformat(product['updated_at'])
        if isinstance(product.get('expiration_date'), str):
            product['expiration_date'] = datetime.fromisoformat(product['expiration_date'])
        
        # Ajouter des indicateurs de tri
        product['_needs_restock'] = product.get('stock', 0) <= product.get('min_stock', 10)
        
        exp_date = product.get('expiration_date')
        if exp_date:
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)
            # Ensure timezone awareness
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            product['_near_expiration'] = exp_date <= expiration_threshold
            product['_days_until_expiration'] = (exp_date - datetime.now(timezone.utc)).days
        else:
            product['_near_expiration'] = False
            product['_days_until_expiration'] = 9999
    
    # Tri par priorité: réappro > péremption proche > alphabétique
    def sort_key(p):
        needs_restock = 0 if p.get('_needs_restock') else 1
        near_expiration = 0 if p.get('_near_expiration') else 1
        days = p.get('_days_until_expiration', 9999)
        name = p.get('name', '').lower()
        return (needs_restock, near_expiration, days, name)
    
    products.sort(key=sort_key)
    
    # Nettoyer les champs temporaires
    for product in products:
        product.pop('_needs_restock', None)
        product.pop('_near_expiration', None)
        product.pop('_days_until_expiration', None)
    
    return products


@router.get("/alerts")
async def get_product_alerts(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Récupérer les alertes: stock bas et péremption proche"""
    tenant_id = current_user['tenant_id']
    
    # Récupérer les paramètres
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    low_stock_threshold = settings.get("low_stock_threshold", 10) if settings else 10
    expiration_alert_days = settings.get("expiration_alert_days", 30) if settings else 30
    expiration_threshold = datetime.now(timezone.utc) + timedelta(days=expiration_alert_days)
    
    products = await db.products.find({"tenant_id": tenant_id, "is_active": {"$ne": False}}, {"_id": 0}).to_list(1000)
    
    low_stock_products = []
    near_expiration_products = []
    expired_products = []
    
    for product in products:
        # Vérifier le stock bas
        if product.get('stock', 0) <= product.get('min_stock', low_stock_threshold):
            low_stock_products.append({
                "id": product['id'],
                "name": product['name'],
                "stock": product.get('stock', 0),
                "min_stock": product.get('min_stock', low_stock_threshold)
            })
        
        # Vérifier la péremption
        exp_date = product.get('expiration_date')
        if exp_date:
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)
            
            # Ensure timezone awareness
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_until = (exp_date - now).days
            
            if exp_date <= now:
                expired_products.append({
                    "id": product['id'],
                    "name": product['name'],
                    "expiration_date": exp_date.isoformat(),
                    "days_expired": abs(days_until)
                })
            elif exp_date <= expiration_threshold:
                near_expiration_products.append({
                    "id": product['id'],
                    "name": product['name'],
                    "expiration_date": exp_date.isoformat(),
                    "days_until_expiration": days_until
                })
    
    # Trier par urgence
    near_expiration_products.sort(key=lambda x: x['days_until_expiration'])
    low_stock_products.sort(key=lambda x: x['stock'])
    
    return {
        "low_stock": {
            "count": len(low_stock_products),
            "threshold": low_stock_threshold,
            "products": low_stock_products
        },
        "near_expiration": {
            "count": len(near_expiration_products),
            "alert_days": expiration_alert_days,
            "products": near_expiration_products
        },
        "expired": {
            "count": len(expired_products),
            "products": expired_products
        }
    }


@router.get("/search")
async def search_products(q: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Search products by name or barcode"""
    products = await db.products.find({
        "tenant_id": current_user['tenant_id'],
        "$or": [
            {"name": {"$regex": q, "$options": "i"}},
            {"barcode": {"$regex": q, "$options": "i"}}
        ]
    }, {"_id": 0}).to_list(50)
    for product in products:
        if isinstance(product.get('created_at'), str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
        if isinstance(product.get('updated_at'), str):
            product['updated_at'] = datetime.fromisoformat(product['updated_at'])
        if isinstance(product.get('expiration_date'), str):
            product['expiration_date'] = datetime.fromisoformat(product['expiration_date'])
    return products


@router.get("/{product_id}", response_model=Product)
async def get_product(product_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get a specific product"""
    product = await db.products.find_one({"id": product_id, "tenant_id": current_user['tenant_id']}, {"_id": 0})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if isinstance(product['created_at'], str):
        product['created_at'] = datetime.fromisoformat(product['created_at'])
    if isinstance(product['updated_at'], str):
        product['updated_at'] = datetime.fromisoformat(product['updated_at'])
    if isinstance(product.get('expiration_date'), str):
        product['expiration_date'] = datetime.fromisoformat(product['expiration_date'])
    return Product(**product)


@router.put("/{product_id}", response_model=Product)
async def update_product(product_id: str, product_data: ProductCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Update a product"""
    existing = await db.products.find_one({"id": product_id, "tenant_id": current_user['tenant_id']})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Vérifier si un autre produit avec le même nom existe
    existing_by_name = await db.products.find_one({
        "tenant_id": current_user['tenant_id'],
        "name": {"$regex": f"^{product_data.name}$", "$options": "i"},
        "id": {"$ne": product_id}
    })
    if existing_by_name:
        raise HTTPException(
            status_code=400,
            detail=f"Un autre produit avec le nom '{product_data.name}' existe déjà"
        )
    
    # Vérifier si un autre produit avec le même code-barres existe
    if product_data.barcode:
        existing_by_barcode = await db.products.find_one({
            "tenant_id": current_user['tenant_id'],
            "barcode": product_data.barcode,
            "id": {"$ne": product_id}
        })
        if existing_by_barcode:
            raise HTTPException(
                status_code=400,
                detail=f"Un autre produit avec le code-barres '{product_data.barcode}' existe déjà ({existing_by_barcode['name']})"
            )
    
    update_data = product_data.model_dump()
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    if update_data.get('expiration_date'):
        update_data['expiration_date'] = update_data['expiration_date'].isoformat()
    
    await db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated_product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if isinstance(updated_product['created_at'], str):
        updated_product['created_at'] = datetime.fromisoformat(updated_product['created_at'])
    if isinstance(updated_product['updated_at'], str):
        updated_product['updated_at'] = datetime.fromisoformat(updated_product['updated_at'])
    if isinstance(updated_product.get('expiration_date'), str):
        updated_product['expiration_date'] = datetime.fromisoformat(updated_product['expiration_date'])
    return Product(**updated_product)


@router.patch("/{product_id}/toggle-status")
async def toggle_product_status(product_id: str, current_user: dict = Depends(require_role(["admin"]))):
    """Toggle product active status (Admin only)"""
    product = await db.products.find_one({"id": product_id, "tenant_id": current_user['tenant_id']})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    new_status = not product.get('is_active', True)
    
    await db.products.update_one(
        {"id": product_id},
        {"$set": {"is_active": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    status_text = "activé" if new_status else "désactivé"
    return {"message": f"Produit {status_text} avec succès", "is_active": new_status}


@router.delete("/{product_id}")
async def delete_product(product_id: str, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Delete a product"""
    # Vérifier si le produit a été vendu au moins une fois
    sales_with_product = await db.sales.count_documents({
        "tenant_id": current_user['tenant_id'],
        "items.product_id": product_id
    })
    if sales_with_product > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Impossible de supprimer ce produit : il a été vendu {sales_with_product} fois. Vous pouvez le désactiver ou modifier son stock à 0."
        )
    
    result = await db.products.delete_one({"id": product_id, "tenant_id": current_user['tenant_id']})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}
