from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from database import db
from auth import get_current_user
from models.returns import SaleReturn, SaleReturnCreate

router = APIRouter(prefix="/returns", tags=["Returns"])

@router.post("", response_model=SaleReturn)
async def create_return(return_data: SaleReturnCreate, current_user: dict = Depends(get_current_user)):
    """Créer un retour d'articles pour une vente"""
    # Vérifier que la vente existe
    sale = await db.sales.find_one({"id": return_data.sale_id, "tenant_id": current_user['tenant_id']})
    if not sale:
        raise HTTPException(status_code=404, detail="Vente non trouvée")
    
    # Vérifier les articles retournés
    return_items = []
    total_refund = 0
    
    for return_item in return_data.items:
        # Trouver l'article dans la vente originale
        sale_item = next((item for item in sale['items'] if item['product_id'] == return_item['product_id']), None)
        if not sale_item:
            raise HTTPException(status_code=400, detail=f"Produit {return_item['product_id']} non trouvé dans cette vente")
        
        # Vérifier la quantité
        if return_item['quantity'] > sale_item['quantity']:
            raise HTTPException(status_code=400, detail=f"Quantité de retour ({return_item['quantity']}) supérieure à la quantité vendue ({sale_item['quantity']}) pour {sale_item['name']}")
        
        # Vérifier si déjà retourné
        existing_returns = await db.returns.find({"sale_id": return_data.sale_id, "tenant_id": current_user['tenant_id']}).to_list(100)
        already_returned = sum(
            sum(ri['quantity'] for ri in r['items'] if ri['product_id'] == return_item['product_id'])
            for r in existing_returns
        )
        
        if already_returned + return_item['quantity'] > sale_item['quantity']:
            raise HTTPException(
                status_code=400, 
                detail=f"Quantité totale retournée ({already_returned + return_item['quantity']}) dépasse la quantité vendue ({sale_item['quantity']}) pour {sale_item['name']}"
            )
        
        item_refund = sale_item['price'] * return_item['quantity']
        total_refund += item_refund
        
        return_items.append({
            "product_id": return_item['product_id'],
            "name": sale_item['name'],
            "quantity": return_item['quantity'],
            "price": sale_item['price'],
            "refund": item_refund
        })
        
        # Restaurer le stock
        product = await db.products.find_one({"id": return_item['product_id'], "tenant_id": current_user['tenant_id']})
        if product:
            new_stock = product['stock'] + return_item['quantity']
            await db.products.update_one({"id": return_item['product_id']}, {"$set": {"stock": new_stock}})
    
    # Créer l'enregistrement de retour
    return_obj = SaleReturn(
        sale_id=return_data.sale_id,
        items=return_items,
        total_refund=total_refund,
        reason=return_data.reason,
        user_id=current_user['user_id'],
        tenant_id=current_user['tenant_id']
    )
    
    doc = return_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.returns.insert_one(doc)
    
    return return_obj

@router.get("", response_model=List[SaleReturn])
async def get_returns(current_user: dict = Depends(get_current_user)):
    """Obtenir tous les retours"""
    returns = await db.returns.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).sort("created_at", -1).to_list(100)
    for r in returns:
        if isinstance(r['created_at'], str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
    return returns

@router.get("/sale/{sale_id}")
async def get_returns_for_sale(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Obtenir les retours pour une vente spécifique"""
    returns = await db.returns.find({"sale_id": sale_id, "tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(100)
    for r in returns:
        if isinstance(r['created_at'], str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
    return returns

@router.get("/history")
async def get_operations_history(current_user: dict = Depends(get_current_user)):
    """Obtenir l'historique complet des opérations (ventes + retours)"""
    # Récupérer les ventes
    sales = await db.sales.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    # Récupérer les retours
    returns = await db.returns.find({"tenant_id": current_user['tenant_id']}, {"_id": 0}).to_list(1000)
    
    # Créer l'historique unifié
    history = []
    
    for sale in sales:
        history.append({
            "id": sale['id'],
            "type": "sale",
            "date": sale['created_at'],
            "amount": sale['total'],
            "items_count": len(sale.get('items', [])),
            "customer_id": sale.get('customer_id'),
            "details": sale
        })
    
    for ret in returns:
        history.append({
            "id": ret['id'],
            "type": "return",
            "date": ret['created_at'],
            "amount": -ret['total_refund'],
            "items_count": len(ret.get('items', [])),
            "sale_id": ret['sale_id'],
            "reason": ret.get('reason'),
            "details": ret
        })
    
    # Trier par date décroissante
    history.sort(key=lambda x: x['date'], reverse=True)
    
    return history
