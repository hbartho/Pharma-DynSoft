from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime, timezone
from database import db
from auth import require_role, get_current_user
from models.supply import Supply, SupplyCreate, SupplyUpdate, SupplyItem, SupplyItemCreate
import uuid

router = APIRouter(prefix="/supplies", tags=["Supplies"])


async def get_product_name(product_id: str, tenant_id: str) -> str:
    """Récupérer le nom d'un produit"""
    product = await db.products.find_one({"id": product_id, "tenant_id": tenant_id})
    return product.get("name", "Produit inconnu") if product else "Produit inconnu"


async def get_supplier_name(supplier_id: str, tenant_id: str) -> str:
    """Récupérer le nom d'un fournisseur"""
    if not supplier_id:
        return None
    supplier = await db.suppliers.find_one({"id": supplier_id, "tenant_id": tenant_id})
    return supplier.get("name", "Fournisseur inconnu") if supplier else "Fournisseur inconnu"


async def get_user_name(user_id: str, tenant_id: str) -> str:
    """Récupérer le nom d'un utilisateur"""
    if not user_id:
        return None
    user = await db.users.find_one({"id": user_id, "tenant_id": tenant_id})
    if user:
        first = user.get("first_name", "")
        last = user.get("last_name", "")
        return f"{first} {last}".strip() or user.get("name", "Utilisateur")
    return "Utilisateur inconnu"


async def enrich_supply(supply: dict, tenant_id: str) -> dict:
    """Enrichir un approvisionnement avec les noms"""
    supply["supplier_name"] = await get_supplier_name(supply.get("supplier_id"), tenant_id)
    supply["created_by_name"] = await get_user_name(supply.get("created_by"), tenant_id)
    supply["updated_by_name"] = await get_user_name(supply.get("updated_by"), tenant_id)
    
    # Enrichir les items
    for item in supply.get("items", []):
        item["product_name"] = await get_product_name(item.get("product_id"), tenant_id)
    
    return supply


@router.post("", response_model=Supply)
async def create_supply(supply_data: SupplyCreate, current_user: dict = Depends(require_role(["admin", "pharmacien"]))):
    """Créer un nouvel approvisionnement (en attente de validation)"""
    tenant_id = current_user["tenant_id"]
    
    # Préparer les items avec les noms de produits
    items = []
    total_amount = 0
    
    for item_data in supply_data.items:
        # Vérifier que le produit existe
        product = await db.products.find_one({"id": item_data.product_id, "tenant_id": tenant_id})
        if not product:
            raise HTTPException(status_code=400, detail=f"Produit {item_data.product_id} non trouvé")
        
        item_total = item_data.quantity * item_data.unit_price
        total_amount += item_total
        
        items.append(SupplyItem(
            id=str(uuid.uuid4()),
            product_id=item_data.product_id,
            product_name=product.get("name"),
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=item_total
        ))
    
    # Créer l'approvisionnement
    supply = Supply(
        supply_date=supply_data.supply_date or datetime.now(timezone.utc),
        is_validated=False,  # Toujours en attente à la création
        supplier_id=supply_data.supplier_id,
        total_amount=total_amount,
        purchase_order_ref=supply_data.purchase_order_ref,
        delivery_note_number=supply_data.delivery_note_number,
        invoice_number=supply_data.invoice_number,
        is_credit_note=supply_data.is_credit_note,
        notes=supply_data.notes,
        items=[item.model_dump() for item in items],
        tenant_id=tenant_id,
        created_by=current_user["user_id"]
    )
    
    # Convertir les dates en ISO string pour MongoDB
    doc = supply.model_dump()
    doc["supply_date"] = doc["supply_date"].isoformat() if doc["supply_date"] else None
    doc["created_at"] = doc["created_at"].isoformat() if doc["created_at"] else None
    
    await db.supplies.insert_one(doc)
    
    # Enrichir pour la réponse
    enriched = await enrich_supply(doc, tenant_id)
    return Supply(**enriched)


@router.get("", response_model=List[Supply])
async def get_supplies(
    status: Optional[str] = None,  # "pending" ou "validated"
    current_user: dict = Depends(get_current_user)
):
    """Récupérer tous les approvisionnements"""
    tenant_id = current_user["tenant_id"]
    
    query = {"tenant_id": tenant_id}
    if status == "pending":
        query["is_validated"] = False
    elif status == "validated":
        query["is_validated"] = True
    
    supplies = await db.supplies.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrichir chaque approvisionnement
    enriched_supplies = []
    for supply in supplies:
        enriched = await enrich_supply(supply, tenant_id)
        # Convertir les dates string en datetime
        for field in ["supply_date", "created_at", "updated_at", "validated_at"]:
            if enriched.get(field) and isinstance(enriched[field], str):
                enriched[field] = datetime.fromisoformat(enriched[field])
        enriched_supplies.append(Supply(**enriched))
    
    return enriched_supplies


@router.get("/{supply_id}", response_model=Supply)
async def get_supply(supply_id: str, current_user: dict = Depends(get_current_user)):
    """Récupérer un approvisionnement par ID"""
    tenant_id = current_user["tenant_id"]
    
    supply = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id}, {"_id": 0})
    if not supply:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    enriched = await enrich_supply(supply, tenant_id)
    for field in ["supply_date", "created_at", "updated_at", "validated_at"]:
        if enriched.get(field) and isinstance(enriched[field], str):
            enriched[field] = datetime.fromisoformat(enriched[field])
    
    return Supply(**enriched)


@router.put("/{supply_id}", response_model=Supply)
async def update_supply(
    supply_id: str,
    supply_data: SupplyUpdate,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Modifier un approvisionnement (seulement si non validé)"""
    tenant_id = current_user["tenant_id"]
    
    # Vérifier que l'appro existe et n'est pas validé
    existing = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    if existing.get("is_validated"):
        raise HTTPException(status_code=400, detail="Impossible de modifier un approvisionnement validé")
    
    # Préparer les items
    items = []
    total_amount = 0
    
    for item_data in supply_data.items:
        product = await db.products.find_one({"id": item_data.product_id, "tenant_id": tenant_id})
        if not product:
            raise HTTPException(status_code=400, detail=f"Produit {item_data.product_id} non trouvé")
        
        item_total = item_data.quantity * item_data.unit_price
        total_amount += item_total
        
        items.append({
            "id": str(uuid.uuid4()),
            "product_id": item_data.product_id,
            "product_name": product.get("name"),
            "quantity": item_data.quantity,
            "unit_price": item_data.unit_price,
            "total_price": item_total
        })
    
    # Mettre à jour
    update_data = {
        "supply_date": supply_data.supply_date.isoformat() if supply_data.supply_date else existing.get("supply_date"),
        "supplier_id": supply_data.supplier_id,
        "purchase_order_ref": supply_data.purchase_order_ref,
        "delivery_note_number": supply_data.delivery_note_number,
        "invoice_number": supply_data.invoice_number,
        "is_credit_note": supply_data.is_credit_note,
        "notes": supply_data.notes,
        "items": items,
        "total_amount": total_amount,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user["id"]
    }
    
    await db.supplies.update_one({"id": supply_id}, {"$set": update_data})
    
    updated = await db.supplies.find_one({"id": supply_id}, {"_id": 0})
    enriched = await enrich_supply(updated, tenant_id)
    for field in ["supply_date", "created_at", "updated_at", "validated_at"]:
        if enriched.get(field) and isinstance(enriched[field], str):
            enriched[field] = datetime.fromisoformat(enriched[field])
    
    return Supply(**enriched)


@router.post("/{supply_id}/validate", response_model=Supply)
async def validate_supply(
    supply_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Valider un approvisionnement et mettre à jour les stocks"""
    tenant_id = current_user["tenant_id"]
    
    # Vérifier que l'appro existe
    supply = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id})
    if not supply:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    if supply.get("is_validated"):
        raise HTTPException(status_code=400, detail="Cet approvisionnement est déjà validé")
    
    if not supply.get("items") or len(supply.get("items", [])) == 0:
        raise HTTPException(status_code=400, detail="Impossible de valider un approvisionnement sans produits")
    
    # Mettre à jour les stocks des produits
    for item in supply.get("items", []):
        product_id = item.get("product_id")
        quantity = item.get("quantity", 0)
        unit_price = item.get("unit_price", 0)
        
        # Mettre à jour le stock et le prix d'achat du produit
        update_fields = {
            "$inc": {"stock": quantity},
            "$set": {
                "purchase_price": unit_price,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
        
        await db.products.update_one(
            {"id": product_id, "tenant_id": tenant_id},
            update_fields
        )
    
    # Marquer l'approvisionnement comme validé
    await db.supplies.update_one(
        {"id": supply_id},
        {"$set": {
            "is_validated": True,
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "validated_by": current_user["id"]
        }}
    )
    
    # Récupérer l'appro mis à jour
    updated = await db.supplies.find_one({"id": supply_id}, {"_id": 0})
    enriched = await enrich_supply(updated, tenant_id)
    for field in ["supply_date", "created_at", "updated_at", "validated_at"]:
        if enriched.get(field) and isinstance(enriched[field], str):
            enriched[field] = datetime.fromisoformat(enriched[field])
    
    return Supply(**enriched)


@router.delete("/{supply_id}")
async def delete_supply(
    supply_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Supprimer un approvisionnement (seulement si non validé)"""
    tenant_id = current_user["tenant_id"]
    
    supply = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id})
    if not supply:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    if supply.get("is_validated"):
        raise HTTPException(status_code=400, detail="Impossible de supprimer un approvisionnement validé")
    
    await db.supplies.delete_one({"id": supply_id})
    return {"message": "Approvisionnement supprimé avec succès"}


@router.post("/{supply_id}/items", response_model=Supply)
async def add_item_to_supply(
    supply_id: str,
    item_data: SupplyItemCreate,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Ajouter un produit à un approvisionnement non validé"""
    tenant_id = current_user["tenant_id"]
    
    supply = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id})
    if not supply:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    if supply.get("is_validated"):
        raise HTTPException(status_code=400, detail="Impossible de modifier un approvisionnement validé")
    
    # Vérifier le produit
    product = await db.products.find_one({"id": item_data.product_id, "tenant_id": tenant_id})
    if not product:
        raise HTTPException(status_code=400, detail="Produit non trouvé")
    
    item_total = item_data.quantity * item_data.unit_price
    new_item = {
        "id": str(uuid.uuid4()),
        "product_id": item_data.product_id,
        "product_name": product.get("name"),
        "quantity": item_data.quantity,
        "unit_price": item_data.unit_price,
        "total_price": item_total
    }
    
    # Ajouter l'item et mettre à jour le total
    new_total = supply.get("total_amount", 0) + item_total
    
    await db.supplies.update_one(
        {"id": supply_id},
        {
            "$push": {"items": new_item},
            "$set": {
                "total_amount": new_total,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["id"]
            }
        }
    )
    
    updated = await db.supplies.find_one({"id": supply_id}, {"_id": 0})
    enriched = await enrich_supply(updated, tenant_id)
    for field in ["supply_date", "created_at", "updated_at", "validated_at"]:
        if enriched.get(field) and isinstance(enriched[field], str):
            enriched[field] = datetime.fromisoformat(enriched[field])
    
    return Supply(**enriched)


@router.delete("/{supply_id}/items/{item_id}")
async def remove_item_from_supply(
    supply_id: str,
    item_id: str,
    current_user: dict = Depends(require_role(["admin", "pharmacien"]))
):
    """Supprimer un produit d'un approvisionnement non validé"""
    tenant_id = current_user["tenant_id"]
    
    supply = await db.supplies.find_one({"id": supply_id, "tenant_id": tenant_id})
    if not supply:
        raise HTTPException(status_code=404, detail="Approvisionnement non trouvé")
    
    if supply.get("is_validated"):
        raise HTTPException(status_code=400, detail="Impossible de modifier un approvisionnement validé")
    
    # Trouver l'item à supprimer
    items = supply.get("items", [])
    item_to_remove = next((item for item in items if item.get("id") == item_id), None)
    
    if not item_to_remove:
        raise HTTPException(status_code=404, detail="Produit non trouvé dans cet approvisionnement")
    
    # Calculer le nouveau total
    new_total = supply.get("total_amount", 0) - item_to_remove.get("total_price", 0)
    
    await db.supplies.update_one(
        {"id": supply_id},
        {
            "$pull": {"items": {"id": item_id}},
            "$set": {
                "total_amount": max(0, new_total),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user["id"]
            }
        }
    )
    
    return {"message": "Produit retiré de l'approvisionnement"}
