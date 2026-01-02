from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.price import PriceHistory, PriceHistoryCreate, PriceChangeType, PriceSummary
import uuid

router = APIRouter(prefix="/prices", tags=["Prices"])


async def get_user_name(user_id: str, tenant_id: str) -> str:
    if not user_id:
        return None
    user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
    if user:
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        return f"{first} {last}".strip() or user.get("name", "Utilisateur")
    return "Utilisateur inconnu"


async def create_price_history(
    product_id: str,
    purchase_price: float,
    selling_price: float,
    change_type: PriceChangeType,
    tenant_id: str,
    user_id: str,
    reference_type: str = None,
    reference_id: str = None,
    notes: str = None
) -> PriceHistory:
    """Créer une entrée d'historique de prix et mettre à jour le produit"""
    # Récupérer le produit
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    purchase_price_before = product.get("purchase_price", 0)
    selling_price_before = product.get("price", 0)
    
    # Créer l'historique
    price_entry = PriceHistory(
        product_id=product_id,
        product_name=product.get("name"),
        purchase_price=purchase_price,
        selling_price=selling_price,
        purchase_price_before=purchase_price_before,
        selling_price_before=selling_price_before,
        change_type=change_type,
        reference_type=reference_type,
        reference_id=reference_id,
        notes=notes,
        tenant_id=tenant_id,
        created_by=user_id
    )
    
    doc = price_entry.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["effective_date"] = doc["effective_date"].isoformat()
    doc["change_type"] = doc["change_type"].value
    
    await db.price_history.insert_one(doc)
    
    # Mettre à jour les prix du produit
    await db.products.update_one(
        {"id": product_id},
        {"$set": {
            "purchase_price": purchase_price,
            "price": selling_price,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return price_entry


@router.get("/history", response_model=List[PriceHistory])
async def get_price_history(
    product_id: Optional[str] = None,
    change_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer l'historique des prix"""
    tenant_id = current_user["tenant_id"]
    
    query = {"tenant_id": tenant_id}
    if product_id:
        query["product_id"] = product_id
    if change_type:
        query["change_type"] = change_type
    
    history = await db.price_history.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    for entry in history:
        entry["created_by_name"] = await get_user_name(entry.get("created_by"), tenant_id)
        for field in ["created_at", "effective_date"]:
            if isinstance(entry.get(field), str):
                entry[field] = datetime.fromisoformat(entry[field])
    
    return [PriceHistory(**entry) for entry in history]


@router.get("/history/{product_id}", response_model=List[PriceHistory])
async def get_product_price_history(
    product_id: str,
    limit: int = Query(default=50, le=200),
    current_user: dict = Depends(get_current_user)
):
    """Récupérer l'historique de prix d'un produit spécifique"""
    tenant_id = current_user["tenant_id"]
    
    history = await db.price_history.find(
        {"product_id": product_id, "tenant_id": tenant_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    for entry in history:
        entry["created_by_name"] = await get_user_name(entry.get("created_by"), tenant_id)
        for field in ["created_at", "effective_date"]:
            if isinstance(entry.get(field), str):
                entry[field] = datetime.fromisoformat(entry[field])
    
    return [PriceHistory(**entry) for entry in history]


@router.post("/update", response_model=PriceHistory)
async def update_product_price(
    data: PriceHistoryCreate,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Mettre à jour le prix d'un produit manuellement"""
    tenant_id = current_user["tenant_id"]
    
    price_entry = await create_price_history(
        product_id=data.product_id,
        purchase_price=data.purchase_price,
        selling_price=data.selling_price,
        change_type=data.change_type or PriceChangeType.MANUAL,
        tenant_id=tenant_id,
        user_id=current_user["id"],
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        notes=data.notes
    )
    
    return price_entry


@router.get("/summary/{product_id}", response_model=PriceSummary)
async def get_price_summary(
    product_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupérer le résumé des prix d'un produit"""
    tenant_id = current_user["tenant_id"]
    
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    if not product:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    
    # Compter les changements de prix
    count = await db.price_history.count_documents({"product_id": product_id, "tenant_id": tenant_id})
    
    last_change = await db.price_history.find_one(
        {"product_id": product_id, "tenant_id": tenant_id},
        {"_id": 0},
        sort=[("created_at", -1)]
    )
    
    last_date = None
    if last_change and last_change.get("created_at"):
        last_date = datetime.fromisoformat(last_change["created_at"]) if isinstance(last_change["created_at"], str) else last_change["created_at"]
    
    return PriceSummary(
        product_id=product_id,
        product_name=product.get("name", "Inconnu"),
        current_purchase_price=product.get("purchase_price", 0),
        current_selling_price=product.get("price", 0),
        price_changes_count=count,
        last_change_date=last_date
    )
