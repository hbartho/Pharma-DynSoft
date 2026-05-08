"""
Routes - PostgreSQL Implementation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
import uuid
import os

from auth import require_role, get_current_user, require_open_shift
from models.sale import Sale, SaleCreate

DATABASE_TYPE = os.environ.get("DATABASE_TYPE", "postgresql")

router = APIRouter(prefix="/sales", tags=["Sales"])

async def generate_sale_number(tenant_id: str = None) -> str:
    """Générer un numéro de vente unique et lisible (ex: VNT-966AAFB0)
    Utilise les 8 premiers caractères de l'UUID pour garantir l'unicité
    """
    unique_id = str(uuid.uuid4()).replace('-', '')[:8].upper()
    return f"VNT-{unique_id}"

if DATABASE_TYPE == "postgresql":
    # ============ PostgreSQL Implementation ============
    from database.repositories_extended import SaleRepository
    from database.repositories import ProductRepository, CustomerRepository, SettingsRepository, UserRepository
    from database.config import db_manager
    from database.models_tenant import DiscountHistory, DiscountSource
    
    def record_discount_history(sale_id, sale_number, sale_data, customer, employee_code, user_name):
        """Enregistre tous les rabais d'une vente dans l'historique."""
        try:
            with db_manager.get_master_session() as session:
                # 1. Rabais par produit (items)
                if hasattr(sale_data, 'items') and sale_data.items:
                    for item in sale_data.items:
                        item_discount = item.get('discount_amount', 0) if isinstance(item, dict) else getattr(item, 'discount_amount', 0)
                        if item_discount and item_discount > 0:
                            history = DiscountHistory(
                                sale_id=sale_id,
                                sale_number=sale_number,
                                discount_source=DiscountSource.PRODUCT,
                                product_id=item.get('product_id') if isinstance(item, dict) else item.product_id,
                                product_name=item.get('product_name') if isinstance(item, dict) else getattr(item, 'product_name', None),
                                customer_id=sale_data.customer_id if sale_data.customer_id else None,
                                customer_name=customer.get('name') if customer else None,
                                discount_type=item.get('discount_type', 'amount') if isinstance(item, dict) else getattr(item, 'discount_type', 'amount'),
                                discount_value=item.get('discount_value', 0) if isinstance(item, dict) else getattr(item, 'discount_value', 0),
                                discount_amount=item_discount,
                                reason=item.get('discount_reason') if isinstance(item, dict) else getattr(item, 'discount_reason', None),
                                agent_code=employee_code,
                                agent_name=user_name
                            )
                            session.add(history)
                
                # 2. Code promo
                promo_discount = getattr(sale_data, 'promo_discount_amount', 0) or 0
                if promo_discount > 0:
                    history = DiscountHistory(
                        sale_id=sale_id,
                        sale_number=sale_number,
                        discount_source=DiscountSource.PROMO_CODE,
                        promo_code=getattr(sale_data, 'promo_code', None),
                        customer_id=sale_data.customer_id if sale_data.customer_id else None,
                        customer_name=customer.get('name') if customer else None,
                        discount_type='amount',
                        discount_value=promo_discount,
                        discount_amount=promo_discount,
                        agent_code=employee_code,
                        agent_name=user_name
                    )
                    session.add(history)
                
                # 3. Rabais automatiques
                auto_discounts = getattr(sale_data, 'automatic_discounts', []) or []
                for auto in auto_discounts:
                    auto_amount = auto.get('discount_amount', 0) if isinstance(auto, dict) else 0
                    if auto_amount > 0:
                        history = DiscountHistory(
                            sale_id=sale_id,
                            sale_number=sale_number,
                            discount_source=DiscountSource.AUTOMATIC,
                            discount_rule_id=auto.get('rule_id') if isinstance(auto, dict) else None,
                            rule_name=auto.get('rule_name') if isinstance(auto, dict) else None,
                            customer_id=sale_data.customer_id if sale_data.customer_id else None,
                            customer_name=customer.get('name') if customer else None,
                            discount_type='amount',
                            discount_value=auto_amount,
                            discount_amount=auto_amount,
                            agent_code=employee_code,
                            agent_name=user_name
                        )
                        session.add(history)
                
                # 4. Rabais manuel (global)
                manual_discount = getattr(sale_data, 'discount_amount', 0) or 0
                promo_discount_val = getattr(sale_data, 'promo_discount_amount', 0) or 0
                auto_discount_val = getattr(sale_data, 'automatic_discount_amount', 0) or 0
                # Le discount_amount global inclut tous les rabais, on doit soustraire les autres
                pure_manual = manual_discount - promo_discount_val - auto_discount_val
                
                # Vérifier si c'est un rabais manuel pur
                if pure_manual > 0 and sale_data.discount_type:
                    history = DiscountHistory(
                        sale_id=sale_id,
                        sale_number=sale_number,
                        discount_source=DiscountSource.MANUAL,
                        customer_id=sale_data.customer_id if sale_data.customer_id else None,
                        customer_name=customer.get('name') if customer else None,
                        discount_type=sale_data.discount_type,
                        discount_value=sale_data.discount_value or 0,
                        discount_amount=pure_manual,
                        agent_code=employee_code,
                        agent_name=user_name
                    )
                    session.add(history)
                
                session.commit()
        except Exception as e:
            print(f"Error recording discount history: {e}")
    
    @router.post("")
    async def create_sale(sale_data: SaleCreate, current_user: dict = Depends(require_open_shift)):
        """
        Create a new sale (PostgreSQL version - simplified without lot management).
        REQUIRES: An open shift for the current user (admin exempt).
        """
        user_id = current_user['user_id']
        employee_code = current_user.get('employee_code', 'N/A')
        user_role = current_user.get('role', 'caissier')
        
        # Repositories
        sale_repo = SaleRepository()
        product_repo = ProductRepository()
        customer_repo = CustomerRepository()
        settings_repo = SettingsRepository()
        
        # Variables pour la gestion de la dette
        has_debt = False
        debt_amount = sale_data.debt_amount or 0
        amount_paid = sale_data.amount_paid if sale_data.amount_paid is not None else sale_data.total
        customer = None
        customer_name = None
        
        # === GESTION DES PAIEMENTS MULTIPLES (SPLIT PAYMENTS) ===
        if sale_data.is_split_payment and sale_data.split_payments:
            total_debt_in_split = 0
            total_paid_in_split = 0
            
            for payment in sale_data.split_payments:
                if payment.get('method') == 'debt':
                    total_debt_in_split += payment.get('amount', 0)
                else:
                    total_paid_in_split += payment.get('amount', 0)
            
            # Calculer le total attendu (après rabais)
            # Note: sale_data.total est le total calculé par le frontend après tous les rabais
            expected_total = float(sale_data.total or 0)
            actual_total_payments = total_paid_in_split + total_debt_in_split
            
            # Vérifier si les paiements couvrent le total
            if total_debt_in_split > 0:
                has_debt = True
                debt_amount = total_debt_in_split
                amount_paid = total_paid_in_split
            elif actual_total_payments < expected_total:
                # Les paiements ne couvrent pas le total - créer une dette pour la différence
                difference = expected_total - actual_total_payments
                if difference > 0.01:  # Tolérance pour les erreurs d'arrondi
                    has_debt = True
                    debt_amount = round(difference, 2)
                    amount_paid = total_paid_in_split
            else:
                amount_paid = total_paid_in_split
        
        # === GESTION DU PAIEMENT SIMPLE (SINGLE PAYMENT) ===
        elif debt_amount > 0 or sale_data.payment_method == 'debt':
            if sale_data.payment_method == 'debt' and debt_amount == 0:
                debt_amount = sale_data.total
                amount_paid = 0
            has_debt = True
        
        # === VALIDATION CLIENT POUR DETTE ===
        if has_debt:
            if not sale_data.customer_id:
                raise HTTPException(
                    status_code=400, 
                    detail="Un client doit être sélectionné pour une vente à crédit"
                )
            
            customer = customer_repo.get_by_id_str(sale_data.customer_id)
            if not customer:
                raise HTTPException(status_code=404, detail="Client non trouvé")
            
            customer_name = customer.get("name")
            max_limit = customer.get("max_debt_limit", 0)
            current_debt = customer.get("current_debt", 0)
            
            if max_limit <= 0:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Le client {customer_name} n'est pas autorisé à acheter à crédit (seuil: 0)"
                )
            
            if current_debt + debt_amount > max_limit:
                available_credit = max(0, max_limit - current_debt)
                raise HTTPException(
                    status_code=400, 
                    detail=f"Crédit insuffisant pour {customer_name}. Disponible: {available_credit:,.0f}, Demandé: {debt_amount:,.0f}"
                )
        
        # Récupérer les infos du client si sélectionné (même sans dette)
        if sale_data.customer_id and not customer:
            customer = customer_repo.get_by_id_str(sale_data.customer_id)
            if customer:
                customer_name = customer.get("name")
        
        # Générer le numéro de vente
        sale_number = await generate_sale_number()
        
        # Préparer les items enrichis
        enriched_items = []
        sale_tva_total = 0
        
        for item in sale_data.items:
            product = product_repo.get_by_id_str(item['product_id'])
            if not product:
                raise HTTPException(status_code=404, detail=f"Produit {item['product_id']} non trouvé")
            
            # Vérifier le stock disponible
            available_stock = product.get('stock', 0)
            if available_stock < item['quantity']:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuffisant pour {product['name']} (disponible: {available_stock}, demandé: {item['quantity']})"
                )
            
            # Déduire le stock du produit
            new_stock = available_stock - item['quantity']
            product_repo.update_by_id_str(item['product_id'], {'stock': new_stock})
            
            # Calculer le prix et sous-total
            unit_price = item.get('unit_price', product.get('price', 0))
            subtotal = item['quantity'] * unit_price
            
            enriched_item = {
                "product_id": item['product_id'],
                "product_name": product.get('name', 'Produit inconnu'),
                "quantity": item['quantity'],
                "unit_price": unit_price,
                "subtotal": round(subtotal, 2),
                "tva_amount": 0,  # TVA non gérée dans cette version simplifiée
            }
            enriched_items.append(enriched_item)
        
        # Calculer le sous-total
        calculated_subtotal = sum(item['subtotal'] for item in enriched_items)
        
        # Calculer le rabais TOTAL (incluant tous les types de rabais)
        # Le frontend envoie:
        # - discount_amount: rabais manuel seulement
        # - promo_discount_amount: rabais code promo
        # - automatic_discount_amount: rabais automatiques
        # - total_discount_amount: somme de tous les rabais
        # - items avec discount_amount: rabais par produit
        manual_discount = float(sale_data.discount_amount or 0)
        promo_discount = float(getattr(sale_data, 'promo_discount_amount', 0) or 0)
        auto_discount = float(getattr(sale_data, 'automatic_discount_amount', 0) or 0)
        
        # Calculer les rabais produit depuis les items
        product_discounts = 0
        if hasattr(sale_data, 'items') and sale_data.items:
            for item in sale_data.items:
                item_discount = item.get('discount_amount', 0) if isinstance(item, dict) else getattr(item, 'discount_amount', 0)
                product_discounts += float(item_discount or 0)
        
        # Total de tous les rabais
        total_discount_amount = manual_discount + promo_discount + auto_discount + product_discounts
        
        # Le total final = sous-total - tous les rabais
        final_total = round(calculated_subtotal - total_discount_amount, 2)
        
        # Préparer les données de vente
        sale_dict = {
            'sale_number': sale_number,
            'customer_id': sale_data.customer_id,
            'customer_name': customer_name,
            'items': enriched_items,
            'subtotal': calculated_subtotal,
            'discount_type': sale_data.discount_type,
            'discount_value': sale_data.discount_value or 0,
            'discount_amount': total_discount_amount,  # Total de tous les rabais
            'total': final_total,
            'total_ht': round(final_total - sale_tva_total, 2),
            'tva_total': round(sale_tva_total, 2),
            'payment_method': sale_data.payment_method,
            'is_split_payment': sale_data.is_split_payment,
            'split_payments': sale_data.split_payments,
            'amount_paid': amount_paid,
            'debt_amount': debt_amount if has_debt else 0,
            'has_debt': has_debt,
            'employee_code': employee_code,
            'user_name': current_user.get('name', employee_code),
        }
        
        # Créer la vente via repository
        result = sale_repo.create(sale_dict, enriched_items)
        
        # Enregistrer les rabais dans l'historique
        if total_discount_amount > 0 or sale_data.promo_code or hasattr(sale_data, 'automatic_discounts'):
            try:
                sale_id_str = result.get('id')
                if sale_id_str:
                    from uuid import UUID
                    sale_uuid = UUID(sale_id_str) if isinstance(sale_id_str, str) else sale_id_str
                    record_discount_history(
                        sale_id=sale_uuid,
                        sale_number=sale_number,
                        sale_data=sale_data,
                        customer=customer,
                        employee_code=employee_code,
                        user_name=current_user.get('name', employee_code)
                    )
            except Exception as e:
                print(f"Warning: Could not record discount history: {e}")
        
        # Ajouter les champs supplémentaires pour la réponse
        result['customer_name'] = customer_name
        result['valuation_method'] = settings_repo.get('stock_valuation_method', 'fefo')
        
        return result
    
    @router.get("")
    async def get_sales(
        page: int = 1,
        limit: int = 20,
        search: str = None,
        date_from: str = None,
        date_to: str = None,
        payment_method: str = None,
        agent_code: str = None,
        customer_id: str = None,
        status: str = None,
        current_user: dict = Depends(get_current_user)
    ):
        """
        Get sales with pagination and filters.
        
        Query params:
        - page: Page number (default: 1)
        - limit: Items per page (default: 20, max: 100)
        - search: Search by sale number, agent name, or agent code
        - date_from: Start date (YYYY-MM-DD)
        - date_to: End date (YYYY-MM-DD)
        - payment_method: Filter by payment method
        - agent_code: Filter by agent code
        - customer_id: Filter by customer ID
        - status: Filter by status (completed, pending, cancelled, all)
        """
        from datetime import datetime as dt
        
        sale_repo = SaleRepository()
        user_repo = UserRepository()
        
        # Valider et limiter les paramètres
        page = max(1, page)
        limit = min(max(1, limit), 100)  # Max 100 items par page
        
        # Parser les dates
        parsed_date_from = None
        parsed_date_to = None
        
        if date_from:
            try:
                parsed_date_from = dt.strptime(date_from, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        if date_to:
            try:
                parsed_date_to = dt.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                pass
        
        # Récupérer les ventes paginées
        result = sale_repo.get_paginated(
            page=page,
            limit=limit,
            search=search,
            date_from=parsed_date_from,
            date_to=parsed_date_to,
            payment_method=payment_method,
            agent_code=agent_code,
            customer_id=customer_id,
            status=status
        )
        
        sales = result["items"]
        
        # Récupérer les utilisateurs pour enrichir les ventes
        users = user_repo.get_all(include_inactive=True)
        users_map = {u['id']: u for u in users}
        users_by_code = {u.get('employee_code'): u for u in users if u.get('employee_code')}
        
        # Enrichir chaque vente avec les infos utilisateur
        for sale in sales:
            if not sale.get('sale_number'):
                sale['sale_number'] = f"VNT-{sale['id'][:8].upper()}"
            
            agent_code_val = sale.get('agent_code')
            agent_name = sale.get('agent_name')
            
            user = None
            if agent_code_val and agent_code_val in users_by_code:
                user = users_by_code[agent_code_val]
            elif sale.get('employee_code') and sale['employee_code'] in users_by_code:
                user = users_by_code[sale['employee_code']]
            elif sale.get('user_id') and sale['user_id'] in users_map:
                user = users_map[sale['user_id']]
            
            if user:
                sale['user_role'] = user.get('role', 'caissier')
                sale['user_name'] = agent_name or user.get('name', 'Inconnu')
                sale['employee_code'] = agent_code_val or user.get('employee_code', 'N/A')
            elif agent_name:
                sale['user_role'] = 'caissier'
                sale['user_name'] = agent_name
                sale['employee_code'] = agent_code_val or 'N/A'
            else:
                sale['user_role'] = 'unknown'
                sale['user_name'] = 'Inconnu'
                sale['employee_code'] = 'N/A'
        
        # Retourner avec les métadonnées de pagination
        return {
            "items": sales,
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "pages": result["pages"]
        }
    
    @router.get("/{sale_id}")
    async def get_sale(sale_id: str, current_user: dict = Depends(get_current_user)):
        """Get a specific sale"""
        sale_repo = SaleRepository()
        sale = sale_repo.get_by_id_str(sale_id)
        
        if not sale:
            raise HTTPException(status_code=404, detail="Sale not found")
        
        # Générer un sale_number si absent
        if not sale.get('sale_number'):
            sale['sale_number'] = f"VNT-{sale['id'][:8].upper()}"
        
        return sale
    
    @router.delete("/{sale_id}")
    async def delete_sale(sale_id: str, current_user: dict = Depends(require_role(["admin"]))):
        """
        Suppression de vente désactivée pour des raisons d'historique et de prévention de fraude.
        Les ventes ne peuvent pas être supprimées une fois enregistrées.
        """
        raise HTTPException(
            status_code=403, 
            detail="La suppression des ventes est désactivée pour des raisons d'historique et de prévention de fraude. Les ventes enregistrées ne peuvent pas être supprimées."
        )

