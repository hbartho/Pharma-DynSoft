from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.product import Product, ProductCreate

router = APIRouter(prefix="/products", tags=["Products"])

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
    
    await db.products.insert_one(doc)
    return product_obj

@router.get("", response_model=List[Product])
async def get_products(current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Get all products"""
    products = await db.products.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
        if isinstance(product['updated_at'], str):
            product['updated_at'] = datetime.fromisoformat(product['updated_at'])
    return products

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
    
    await db.products.update_one({"id": product_id}, {"$set": update_data})
    
    updated_product = await db.products.find_one({"id": product_id}, {"_id": 0})
    if isinstance(updated_product['created_at'], str):
        updated_product['created_at'] = datetime.fromisoformat(updated_product['created_at'])
    if isinstance(updated_product['updated_at'], str):
        updated_product['updated_at'] = datetime.fromisoformat(updated_product['updated_at'])
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
