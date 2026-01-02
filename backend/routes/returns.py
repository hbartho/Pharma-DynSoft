from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone, timedelta
from database import db
from auth import get_current_user
from models.returns import SaleReturn, SaleReturnCreate

router = APIRouter(prefix="/returns", tags=["Returns"])


async def generate_return_number(tenant_id: str) -> str:
    """Générer un numéro de retour unique et lisible (ex: RET-0001)"""
    count = await db.returns.count_documents({"tenant_id": tenant_id})
    return f"RET-{str(count + 1).zfill(4)}"


async def get_return_delay_days(tenant_id: str) -> int:
    """Récupérer le délai de retour configuré dans les paramètres"""
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if settings:
        return settings.get("return_delay_days", 3)  # 3 jours par défaut
    return 3


async def check_sale_return_eligibility(sale: dict, tenant_id: str) -> tuple:
    """
    Vérifier si une vente est éligible au retour.
    Retourne (is_eligible, message, days_remaining)
    """
    return_delay_days = await get_return_delay_days(tenant_id)
    
    # Parser la date de la vente
    sale_date = sale.get('created_at')
    if isinstance(sale_date, str):
        sale_date = datetime.fromisoformat(sale_date.replace('Z', '+00:00'))
    
    # Calculer la date limite de retour
    deadline = sale_date + timedelta(days=return_delay_days)
    now = datetime.now(timezone.utc)
    
    # Vérifier si le délai est dépassé
    if now > deadline:
        days_elapsed = (now - sale_date).days
        return (
            False, 
            f"Le délai de retour de {return_delay_days} jour(s) est dépassé. Cette vente date de {days_elapsed} jour(s).",
            0
        )
    
    # Calculer les jours restants
    days_remaining = (deadline - now).days
    return (True, f"{days_remaining} jour(s) restant(s) pour le retour", days_remaining)


@router.post("", response_model=SaleReturn)
async def create_return(return_data: SaleReturnCreate, current_user: dict = Depends(get_current_user)):
    """Créer un retour d'articles pour une vente"""
    tenant_id = current_user['tenant_id']
    employee_code = current_user.get('employee_code', 'N/A')
    
    # Vérifier que le motif est fourni
    if not return_data.reason or not return_data.reason.strip():
        raise HTTPException(status_code=400, detail="Le motif du retour est obligatoire")
    
    # Vérifier que la vente existe
    sale = await db.sales.find_one({"id": return_data.sale_id, "tenant_id": tenant_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Vente non trouvée")
    
    # ⚠️ NOUVELLE VALIDATION : Vérifier le délai de retour
    is_eligible, message, _ = await check_sale_return_eligibility(sale, tenant_id)
    if not is_eligible:
        raise HTTPException(status_code=400, detail=message)
    
    # Récupérer le numéro de vente (ou générer un fallback)
    sale_number = sale.get('sale_number') or f"VNT-{sale['id'][:8].upper()}"
    
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
        existing_returns = await db.returns.find({"sale_id": return_data.sale_id, "tenant_id": tenant_id}).to_list(100)
        already_returned = sum(
            sum(ri['quantity'] for ri in r['items'] if ri['product_id'] == return_item['product_id'])
            for r in existing_returns
        )
        
        if already_returned + return_item['quantity'] > sale_item['quantity']:
            raise HTTPException(
                status_code=400, 
                detail=f"Quantité totale retournée ({already_returned + return_item['quantity']}) dépasse la quantité vendue ({sale_item['quantity']}) pour {sale_item['name']}"
            )
        
        item_refund = round(sale_item['price'] * return_item['quantity'], 2)
        total_refund += item_refund
        
        return_items.append({
            "product_id": return_item['product_id'],
            "name": sale_item['name'],
            "quantity": return_item['quantity'],
            "price": sale_item['price'],
            "refund": item_refund
        })
        
        # Restaurer le stock
        product = await db.products.find_one({"id": return_item['product_id'], "tenant_id": tenant_id})
        if product:
            new_stock = product['stock'] + return_item['quantity']
            await db.products.update_one({"id": return_item['product_id']}, {"$set": {"stock": new_stock}})
    
    # Générer le numéro de retour
    return_number = await generate_return_number(tenant_id)
    
    # Créer l'enregistrement de retour avec le numéro de vente
    return_obj = SaleReturn(
        return_number=return_number,
        sale_id=return_data.sale_id,
        sale_number=sale_number,  # Inclure le numéro de vente
        items=return_items,
        total_refund=round(total_refund, 2),
        reason=return_data.reason,
        user_id=current_user['user_id'],
        employee_code=employee_code,  # Utiliser employee_code
        tenant_id=tenant_id
    )
    
    doc = return_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.returns.insert_one(doc)
    
    return return_obj


@router.get("/check-eligibility/{sale_id}")
async def check_return_eligibility(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Vérifier si une vente est éligible au retour (délai non dépassé)"""
    tenant_id = current_user['tenant_id']
    
    sale = await db.sales.find_one({"id": sale_id, "tenant_id": tenant_id})
    if not sale:
        raise HTTPException(status_code=404, detail="Vente non trouvée")
    
    is_eligible, message, days_remaining = await check_sale_return_eligibility(sale, tenant_id)
    return_delay_days = await get_return_delay_days(tenant_id)
    
    return {
        "sale_id": sale_id,
        "is_eligible": is_eligible,
        "message": message,
        "days_remaining": days_remaining,
        "return_delay_days": return_delay_days
    }


@router.get("", response_model=List[SaleReturn])
async def get_returns(current_user: dict = Depends(get_current_user)):
    """Obtenir tous les retours avec le numéro de vente"""
    tenant_id = current_user['tenant_id']
    returns = await db.returns.find({"tenant_id": tenant_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # Récupérer tous les utilisateurs pour enrichir les données
    users = await db.users.find({"tenant_id": tenant_id}, {"_id": 0, "password": 0}).to_list(1000)
    users_map = {u['id']: u for u in users}
    
    for r in returns:
        if isinstance(r['created_at'], str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        
        # Générer un return_number si absent (pour les anciens retours)
        if not r.get('return_number'):
            r['return_number'] = f"RET-{r['id'][:8].upper()}"
        
        # Récupérer le numéro de vente si absent
        if not r.get('sale_number') and r.get('sale_id'):
            sale = await db.sales.find_one({"id": r['sale_id'], "tenant_id": tenant_id}, {"_id": 0})
            if sale:
                r['sale_number'] = sale.get('sale_number') or f"VNT-{sale['id'][:8].upper()}"
            else:
                r['sale_number'] = f"VNT-{r['sale_id'][:8].upper()}"
        
        # Ajouter employee_code si absent
        if not r.get('employee_code') and r.get('user_id'):
            user = users_map.get(r['user_id'])
            if user:
                if user.get('employee_code'):
                    r['employee_code'] = user['employee_code']
                else:
                    role_prefix = {'admin': 'ADM', 'pharmacien': 'PHA', 'caissier': 'CAI'}.get(user.get('role', ''), 'EMP')
                    r['employee_code'] = f"{role_prefix}-{user['id'][:4].upper()}"
            else:
                r['employee_code'] = 'N/A'
    
    return returns


@router.get("/sale/{sale_id}")
async def get_returns_for_sale(sale_id: str, current_user: dict = Depends(get_current_user)):
    """Obtenir les retours pour une vente spécifique"""
    tenant_id = current_user['tenant_id']
    returns = await db.returns.find({"sale_id": sale_id, "tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    
    # Récupérer le numéro de vente
    sale = await db.sales.find_one({"id": sale_id, "tenant_id": tenant_id}, {"_id": 0})
    sale_number = None
    if sale:
        sale_number = sale.get('sale_number') or f"VNT-{sale['id'][:8].upper()}"
    
    for r in returns:
        if isinstance(r['created_at'], str):
            r['created_at'] = datetime.fromisoformat(r['created_at'])
        
        # Ajouter le numéro de vente si absent
        if not r.get('sale_number'):
            r['sale_number'] = sale_number or f"VNT-{sale_id[:8].upper()}"
        
        # Générer un return_number si absent
        if not r.get('return_number'):
            r['return_number'] = f"RET-{r['id'][:8].upper()}"
    
    return returns


@router.get("/history")
async def get_operations_history(current_user: dict = Depends(get_current_user)):
    """Obtenir l'historique complet des opérations (ventes + retours) avec informations agent"""
    tenant_id = current_user['tenant_id']
    
    # Récupérer les ventes
    sales = await db.sales.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    
    # Récupérer les retours
    returns = await db.returns.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(1000)
    
    # Récupérer tous les utilisateurs pour enrichir les données
    users = await db.users.find({"tenant_id": tenant_id}, {"_id": 0, "password": 0}).to_list(1000)
    users_map = {u['id']: u for u in users}
    
    # Créer un map des ventes pour récupérer les numéros de vente
    sales_map = {s['id']: s for s in sales}
    
    # Récupérer le délai de retour configuré
    return_delay_days = await get_return_delay_days(tenant_id)
    
    def get_user_info(user_id, existing_employee_code=None):
        """Récupère les informations de l'agent"""
        if existing_employee_code:
            return {
                'employee_code': existing_employee_code,
                'user_role': users_map.get(user_id, {}).get('role', 'unknown') if user_id else 'unknown',
                'user_name': users_map.get(user_id, {}).get('name') or 'Inconnu' if user_id else 'Inconnu'
            }
        
        if user_id and user_id in users_map:
            user = users_map[user_id]
            if 'employee_code' in user and user['employee_code']:
                employee_code = user['employee_code']
            else:
                role_prefix = {'admin': 'ADM', 'pharmacien': 'PHA', 'caissier': 'CAI'}.get(user.get('role', ''), 'EMP')
                employee_code = f"{role_prefix}-{user['id'][:4].upper()}"
            user_name = user.get('name') or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            return {
                'employee_code': employee_code,
                'user_role': user.get('role', 'unknown'),
                'user_name': user_name or 'Inconnu'
            }
        return {
            'employee_code': 'N/A',
            'user_role': 'unknown',
            'user_name': 'Inconnu'
        }
    
    def check_return_eligibility(sale_date_str):
        """Vérifier si une vente est encore éligible au retour"""
        if isinstance(sale_date_str, str):
            sale_date = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00'))
        else:
            sale_date = sale_date_str
        
        deadline = sale_date + timedelta(days=return_delay_days)
        now = datetime.now(timezone.utc)
        
        if now > deadline:
            return False, 0
        return True, (deadline - now).days
    
    # Créer l'historique unifié
    history = []
    
    for sale in sales:
        user_info = get_user_info(sale.get('user_id'), sale.get('employee_code'))
        sale_number = sale.get('sale_number') or f"VNT-{sale['id'][:8].upper()}"
        
        # Vérifier l'éligibilité au retour
        is_returnable, days_remaining = check_return_eligibility(sale['created_at'])
        
        history.append({
            "id": sale['id'],
            "operation_number": sale_number,
            "type": "sale",
            "date": sale['created_at'],
            "amount": sale['total'],
            "items_count": len(sale.get('items', [])),
            "customer_id": sale.get('customer_id'),
            "user_id": sale.get('user_id'),
            "is_returnable": is_returnable,
            "return_days_remaining": days_remaining,
            **user_info,
            "details": sale
        })
    
    for ret in returns:
        user_info = get_user_info(ret.get('user_id'), ret.get('employee_code'))
        return_number = ret.get('return_number') or f"RET-{ret['id'][:8].upper()}"
        
        # Récupérer le numéro de vente
        sale_number = ret.get('sale_number')
        if not sale_number and ret.get('sale_id'):
            sale = sales_map.get(ret['sale_id'])
            if sale:
                sale_number = sale.get('sale_number') or f"VNT-{sale['id'][:8].upper()}"
            else:
                sale_number = f"VNT-{ret['sale_id'][:8].upper()}"
        
        history.append({
            "id": ret['id'],
            "operation_number": return_number,
            "type": "return",
            "date": ret['created_at'],
            "amount": -ret['total_refund'],
            "items_count": len(ret.get('items', [])),
            "sale_id": ret['sale_id'],
            "sale_number": sale_number,  # Numéro de vente associé au retour
            "reason": ret.get('reason'),
            "user_id": ret.get('user_id'),
            **user_info,
            "details": ret
        })
    
    # Trier par date décroissante
    history.sort(key=lambda x: x['date'], reverse=True)
    
    return history
