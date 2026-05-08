"""
Routes API pour la gestion des rabais.
- Codes promo (CRUD + validation)
- Règles de rabais automatiques (CRUD)
- Historique des rabais
- Calcul des rabais applicables
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

from database.config import db_manager
from database.models_tenant import (
    PromoCode, PromoCodeStatus, PromoCodeUsage,
    DiscountRule, DiscountRuleType,
    DiscountHistory, DiscountSource,
    Sale, Customer, Product
)
from auth import get_current_user, require_role
from sqlalchemy import func, or_

router = APIRouter(prefix="/discounts", tags=["Discounts"])
logger = logging.getLogger(__name__)


# ===================== SCHEMAS =====================

class PromoCodeCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    discount_type: str  # 'percent' ou 'amount'
    discount_value: float
    min_purchase_amount: float = 0
    max_discount_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: int = 1
    applicable_categories: Optional[List[str]] = None
    applicable_products: Optional[List[str]] = None
    first_purchase_only: bool = False


class PromoCodeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_purchase_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    max_uses: Optional[int] = None
    max_uses_per_customer: Optional[int] = None
    applicable_categories: Optional[List[str]] = None
    applicable_products: Optional[List[str]] = None
    first_purchase_only: Optional[bool] = None


class DiscountRuleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_type: str
    discount_type: str
    discount_value: float
    max_discount_amount: Optional[float] = None
    conditions: Optional[dict] = None
    priority: int = 0
    is_cumulative: bool = False
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class DiscountRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount_amount: Optional[float] = None
    conditions: Optional[dict] = None
    priority: Optional[int] = None
    is_cumulative: Optional[bool] = None
    is_active: Optional[bool] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ValidatePromoCodeRequest(BaseModel):
    code: str
    cart_subtotal: float
    customer_id: Optional[str] = None
    cart_items: Optional[List[dict]] = None


class CalculateDiscountsRequest(BaseModel):
    cart_subtotal: float
    customer_id: Optional[str] = None
    cart_items: List[dict]
    promo_code: Optional[str] = None


# ===================== PROMO CODES =====================

@router.get("/promo-codes")
async def list_promo_codes(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Liste tous les codes promo."""
    with db_manager.get_master_session() as session:
        query = session.query(PromoCode)
        
        if status:
            query = query.filter(PromoCode.status == status)
        
        if search:
            query = query.filter(
                or_(
                    PromoCode.code.ilike(f"%{search}%"),
                    PromoCode.name.ilike(f"%{search}%")
                )
            )
        
        total = query.count()
        codes = query.order_by(PromoCode.created_at.desc()).offset(skip).limit(limit).all()
        
        return {
            "items": [_promo_code_to_dict(c) for c in codes],
            "total": total
        }


@router.post("/promo-codes")
async def create_promo_code(
    data: PromoCodeCreate,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Crée un nouveau code promo."""
    with db_manager.get_master_session() as session:
        # Vérifier unicité du code
        existing = session.query(PromoCode).filter(PromoCode.code == data.code.upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ce code promo existe déjà")
        
        promo = PromoCode(
            code=data.code.upper(),
            name=data.name,
            description=data.description,
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            min_purchase_amount=data.min_purchase_amount,
            max_discount_amount=data.max_discount_amount,
            start_date=data.start_date,
            end_date=data.end_date,
            max_uses=data.max_uses,
            max_uses_per_customer=data.max_uses_per_customer,
            applicable_categories=data.applicable_categories,
            applicable_products=data.applicable_products,
            first_purchase_only=data.first_purchase_only,
            created_by=current_user.get("employee_code")
        )
        
        session.add(promo)
        session.flush()
        result = _promo_code_to_dict(promo)
        
        return result


@router.get("/promo-codes/{promo_id}")
async def get_promo_code(
    promo_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupère un code promo par ID."""
    with db_manager.get_master_session() as session:
        promo = session.query(PromoCode).filter(PromoCode.id == promo_id).first()
        if not promo:
            raise HTTPException(status_code=404, detail="Code promo non trouvé")
        return _promo_code_to_dict(promo)


@router.put("/promo-codes/{promo_id}")
async def update_promo_code(
    promo_id: str,
    data: PromoCodeUpdate,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Met à jour un code promo."""
    with db_manager.get_master_session() as session:
        promo = session.query(PromoCode).filter(PromoCode.id == promo_id).first()
        if not promo:
            raise HTTPException(status_code=404, detail="Code promo non trouvé")
        
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key == "status" and value:
                setattr(promo, key, PromoCodeStatus(value))
            else:
                setattr(promo, key, value)
        
        session.flush()
        return _promo_code_to_dict(promo)


@router.delete("/promo-codes/{promo_id}")
async def delete_promo_code(
    promo_id: str,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Supprime un code promo."""
    with db_manager.get_master_session() as session:
        promo = session.query(PromoCode).filter(PromoCode.id == promo_id).first()
        if not promo:
            raise HTTPException(status_code=404, detail="Code promo non trouvé")
        
        session.delete(promo)
        return {"message": "Code promo supprimé"}


@router.post("/promo-codes/validate")
async def validate_promo_code(
    data: ValidatePromoCodeRequest,
    current_user: dict = Depends(get_current_user)
):
    """Valide un code promo et retourne le rabais applicable."""
    code = data.code.upper().strip()
    
    with db_manager.get_master_session() as session:
        promo = session.query(PromoCode).filter(PromoCode.code == code).first()
        if not promo:
            raise HTTPException(status_code=404, detail="Code promo invalide")
        
        # Vérifier le statut
        if promo.status != PromoCodeStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Ce code promo n'est plus actif")
        
        # Vérifier les dates
        now = datetime.utcnow()
        if promo.start_date and now < promo.start_date:
            raise HTTPException(status_code=400, detail="Ce code promo n'est pas encore valide")
        if promo.end_date and now > promo.end_date:
            raise HTTPException(status_code=400, detail="Ce code promo a expiré")
        
        # Vérifier le nombre max d'utilisations
        if promo.max_uses and promo.current_uses >= promo.max_uses:
            raise HTTPException(status_code=400, detail="Ce code promo a atteint son nombre maximum d'utilisations")
        
        # Vérifier le montant minimum
        if data.cart_subtotal < promo.min_purchase_amount:
            raise HTTPException(
                status_code=400, 
                detail=f"Montant minimum requis: {promo.min_purchase_amount} GNF"
            )
        
        # Vérifier l'utilisation par client
        if data.customer_id and promo.max_uses_per_customer:
            usage_count = session.query(PromoCodeUsage).filter(
                PromoCodeUsage.promo_code_id == promo.id,
                PromoCodeUsage.customer_id == data.customer_id
            ).count()
            if usage_count >= promo.max_uses_per_customer:
                raise HTTPException(status_code=400, detail="Vous avez déjà utilisé ce code promo")
        
        # Vérifier première commande uniquement
        if promo.first_purchase_only and data.customer_id:
            previous_sales = session.query(Sale).filter(Sale.customer_id == data.customer_id).count()
            if previous_sales > 0:
                raise HTTPException(status_code=400, detail="Ce code est réservé aux nouveaux clients")
        
        # Calculer le rabais
        if promo.discount_type == "percent":
            discount_amount = round(data.cart_subtotal * promo.discount_value / 100)
            if promo.max_discount_amount:
                discount_amount = min(discount_amount, promo.max_discount_amount)
        else:
            discount_amount = min(promo.discount_value, data.cart_subtotal)
        
        return {
            "valid": True,
            "promo_code": _promo_code_to_dict(promo),
            "discount_amount": discount_amount,
            "discount_type": promo.discount_type,
            "discount_value": promo.discount_value
        }


# ===================== DISCOUNT RULES =====================

@router.get("/rules")
async def list_discount_rules(
    rule_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """Liste toutes les règles de rabais."""
    with db_manager.get_master_session() as session:
        query = session.query(DiscountRule)
        
        if rule_type:
            query = query.filter(DiscountRule.rule_type == rule_type)
        
        if is_active is not None:
            query = query.filter(DiscountRule.is_active == is_active)
        
        rules = query.order_by(DiscountRule.priority.desc()).all()
        
        return {
            "items": [_discount_rule_to_dict(r) for r in rules],
            "total": len(rules)
        }


@router.post("/rules")
async def create_discount_rule(
    data: DiscountRuleCreate,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Crée une nouvelle règle de rabais."""
    with db_manager.get_master_session() as session:
        rule = DiscountRule(
            name=data.name,
            description=data.description,
            rule_type=DiscountRuleType(data.rule_type),
            discount_type=data.discount_type,
            discount_value=data.discount_value,
            max_discount_amount=data.max_discount_amount,
            conditions=data.conditions,
            priority=data.priority,
            is_cumulative=data.is_cumulative,
            start_date=data.start_date,
            end_date=data.end_date,
            created_by=current_user.get("employee_code")
        )
        
        session.add(rule)
        session.flush()
        return _discount_rule_to_dict(rule)


@router.get("/rules/{rule_id}")
async def get_discount_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Récupère une règle par ID."""
    with db_manager.get_master_session() as session:
        rule = session.query(DiscountRule).filter(DiscountRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Règle non trouvée")
        return _discount_rule_to_dict(rule)


@router.put("/rules/{rule_id}")
async def update_discount_rule(
    rule_id: str,
    data: DiscountRuleUpdate,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Met à jour une règle de rabais."""
    with db_manager.get_master_session() as session:
        rule = session.query(DiscountRule).filter(DiscountRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Règle non trouvée")
        
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rule, key, value)
        
        session.flush()
        return _discount_rule_to_dict(rule)


@router.delete("/rules/{rule_id}")
async def delete_discount_rule(
    rule_id: str,
    current_user: dict = Depends(require_role(["admin"]))
):
    """Supprime une règle de rabais."""
    with db_manager.get_master_session() as session:
        rule = session.query(DiscountRule).filter(DiscountRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Règle non trouvée")
        
        session.delete(rule)
        return {"message": "Règle supprimée"}


# ===================== CALCULATE APPLICABLE DISCOUNTS =====================

@router.post("/calculate")
async def calculate_applicable_discounts(
    data: CalculateDiscountsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Calcule tous les rabais applicables pour un panier donné.
    """
    applicable_discounts = []
    total_automatic_discount = 0
    promo_discount = None
    
    with db_manager.get_master_session() as session:
        # Charger le client si fourni
        customer = None
        if data.customer_id:
            customer = session.query(Customer).filter(Customer.id == data.customer_id).first()
        
        # 1. Vérifier les règles automatiques
        now = datetime.utcnow()
        active_rules = session.query(DiscountRule).filter(
            DiscountRule.is_active == True,
            or_(DiscountRule.start_date == None, DiscountRule.start_date <= now),
            or_(DiscountRule.end_date == None, DiscountRule.end_date >= now)
        ).order_by(DiscountRule.priority.desc()).all()
        
        for rule in active_rules:
            discount_result = _check_rule_applicability(rule, data, customer, session)
            if discount_result:
                applicable_discounts.append(discount_result)
                if rule.is_cumulative or len(applicable_discounts) == 1:
                    total_automatic_discount += discount_result["discount_amount"]
        
        # 2. Vérifier le code promo
        if data.promo_code:
            try:
                promo_result = await validate_promo_code(
                    ValidatePromoCodeRequest(
                        code=data.promo_code,
                        cart_subtotal=data.cart_subtotal,
                        customer_id=data.customer_id,
                        cart_items=data.cart_items
                    ),
                    current_user=current_user
                )
                promo_discount = {
                    "source": "promo_code",
                    "code": data.promo_code,
                    "discount_type": promo_result["discount_type"],
                    "discount_value": promo_result["discount_value"],
                    "discount_amount": promo_result["discount_amount"]
                }
            except HTTPException:
                pass
        
        # Calculer le total
        total_discount = total_automatic_discount
        if promo_discount:
            total_discount += promo_discount["discount_amount"]
        
        return {
            "automatic_discounts": applicable_discounts,
            "promo_discount": promo_discount,
            "total_automatic_discount": total_automatic_discount,
            "total_discount": total_discount,
            "original_subtotal": data.cart_subtotal,
            "final_total": max(0, data.cart_subtotal - total_discount)
        }


def _check_rule_applicability(rule: DiscountRule, data: CalculateDiscountsRequest, customer, session) -> Optional[dict]:
    """Vérifie si une règle s'applique et retourne le rabais."""
    conditions = rule.conditions or {}
    discount_amount = 0
    
    if rule.rule_type == DiscountRuleType.LOYALTY:
        if not customer:
            return None
        min_purchases = conditions.get("min_purchases", 50)
        purchase_count = session.query(Sale).filter(Sale.customer_id == customer.id).count()
        if purchase_count < min_purchases:
            return None
        discount_amount = _calculate_discount(rule, data.cart_subtotal)
    
    elif rule.rule_type == DiscountRuleType.VOLUME:
        min_amount = conditions.get("min_amount", 100000)
        if data.cart_subtotal < min_amount:
            return None
        discount_amount = _calculate_discount(rule, data.cart_subtotal)
    
    elif rule.rule_type == DiscountRuleType.CATEGORY:
        category_ids = conditions.get("category_ids", [])
        min_quantity = conditions.get("min_quantity", 1)
        
        matching_items = [
            item for item in data.cart_items 
            if item.get("category_id") in category_ids
        ]
        total_qty = sum(item.get("quantity", 0) for item in matching_items)
        
        if total_qty < min_quantity:
            return None
        
        category_subtotal = sum(item.get("subtotal", 0) for item in matching_items)
        discount_amount = _calculate_discount(rule, category_subtotal)
    
    elif rule.rule_type == DiscountRuleType.EXPIRATION:
        days_threshold = conditions.get("days_before_expiry", 30)
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
        
        expiring_subtotal = 0
        for item in data.cart_items:
            expiry_date = item.get("expiry_date")
            if expiry_date:
                if isinstance(expiry_date, str):
                    try:
                        expiry_date = datetime.fromisoformat(expiry_date.replace("Z", "+00:00"))
                    except:
                        continue
                if expiry_date <= threshold_date:
                    expiring_subtotal += item.get("subtotal", 0)
        
        if expiring_subtotal == 0:
            return None
        
        discount_amount = _calculate_discount(rule, expiring_subtotal)
    
    else:
        return None
    
    if discount_amount <= 0:
        return None
    
    return {
        "source": "automatic",
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "rule_type": rule.rule_type.value,
        "discount_type": rule.discount_type,
        "discount_value": rule.discount_value,
        "discount_amount": discount_amount,
        "is_cumulative": rule.is_cumulative
    }


def _calculate_discount(rule: DiscountRule, subtotal: float) -> float:
    """Calcule le montant du rabais selon la règle."""
    if rule.discount_type == "percent":
        discount = round(subtotal * rule.discount_value / 100)
        if rule.max_discount_amount:
            discount = min(discount, rule.max_discount_amount)
    else:
        discount = min(rule.discount_value, subtotal)
    
    return discount


# ===================== DISCOUNT HISTORY =====================

@router.get("/history")
async def get_discount_history(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    source: Optional[str] = None,
    agent_code: Optional[str] = None,
    customer_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user)
):
    """Récupère l'historique des rabais accordés."""
    with db_manager.get_master_session() as session:
        query = session.query(DiscountHistory)
        
        if date_from:
            query = query.filter(DiscountHistory.created_at >= date_from)
        if date_to:
            query = query.filter(DiscountHistory.created_at <= date_to)
        if source:
            query = query.filter(DiscountHistory.discount_source == source)
        if agent_code:
            query = query.filter(DiscountHistory.agent_code == agent_code)
        if customer_id:
            query = query.filter(DiscountHistory.customer_id == customer_id)
        
        total = query.count()
        history = query.order_by(DiscountHistory.created_at.desc()).offset(skip).limit(limit).all()
        
        return {
            "items": [_discount_history_to_dict(h) for h in history],
            "total": total
        }


@router.get("/history/stats")
async def get_discount_stats(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Statistiques des rabais accordés."""
    with db_manager.get_master_session() as session:
        query = session.query(DiscountHistory)
        
        if date_from:
            query = query.filter(DiscountHistory.created_at >= date_from)
        if date_to:
            query = query.filter(DiscountHistory.created_at <= date_to)
        
        # Total par source
        stats_by_source = session.query(
            DiscountHistory.discount_source,
            func.count(DiscountHistory.id).label("count"),
            func.sum(DiscountHistory.discount_amount).label("total_amount")
        ).group_by(DiscountHistory.discount_source)
        
        if date_from:
            stats_by_source = stats_by_source.filter(DiscountHistory.created_at >= date_from)
        if date_to:
            stats_by_source = stats_by_source.filter(DiscountHistory.created_at <= date_to)
        
        by_source = {}
        for row in stats_by_source.all():
            source_key = row[0].value if row[0] else "unknown"
            by_source[source_key] = {"count": row[1], "total": row[2] or 0}
        
        # Total par agent
        stats_by_agent = session.query(
            DiscountHistory.agent_code,
            DiscountHistory.agent_name,
            func.count(DiscountHistory.id).label("count"),
            func.sum(DiscountHistory.discount_amount).label("total_amount")
        ).group_by(DiscountHistory.agent_code, DiscountHistory.agent_name)
        
        if date_from:
            stats_by_agent = stats_by_agent.filter(DiscountHistory.created_at >= date_from)
        if date_to:
            stats_by_agent = stats_by_agent.filter(DiscountHistory.created_at <= date_to)
        
        by_agent = [
            {"agent_code": row[0], "agent_name": row[1], "count": row[2], "total": row[3] or 0}
            for row in stats_by_agent.all()
        ]
        
        # Total général
        total_discounts = query.count()
        total_amount = session.query(func.sum(DiscountHistory.discount_amount)).scalar() or 0
        
        return {
            "total_discounts": total_discounts,
            "total_amount": total_amount,
            "by_source": by_source,
            "by_agent": by_agent
        }


# ===================== HELPERS =====================

def _promo_code_to_dict(promo: PromoCode) -> dict:
    return {
        "id": str(promo.id),
        "code": promo.code,
        "name": promo.name,
        "description": promo.description,
        "discount_type": promo.discount_type,
        "discount_value": promo.discount_value,
        "min_purchase_amount": promo.min_purchase_amount,
        "max_discount_amount": promo.max_discount_amount,
        "start_date": promo.start_date.isoformat() if promo.start_date else None,
        "end_date": promo.end_date.isoformat() if promo.end_date else None,
        "status": promo.status.value if promo.status else None,
        "max_uses": promo.max_uses,
        "max_uses_per_customer": promo.max_uses_per_customer,
        "current_uses": promo.current_uses,
        "applicable_categories": promo.applicable_categories,
        "applicable_products": promo.applicable_products,
        "first_purchase_only": promo.first_purchase_only,
        "created_at": promo.created_at.isoformat() if promo.created_at else None,
        "created_by": promo.created_by
    }


def _discount_rule_to_dict(rule: DiscountRule) -> dict:
    return {
        "id": str(rule.id),
        "name": rule.name,
        "description": rule.description,
        "rule_type": rule.rule_type.value if rule.rule_type else None,
        "discount_type": rule.discount_type,
        "discount_value": rule.discount_value,
        "max_discount_amount": rule.max_discount_amount,
        "conditions": rule.conditions,
        "priority": rule.priority,
        "is_cumulative": rule.is_cumulative,
        "is_active": rule.is_active,
        "start_date": rule.start_date.isoformat() if rule.start_date else None,
        "end_date": rule.end_date.isoformat() if rule.end_date else None,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "created_by": rule.created_by
    }


def _discount_history_to_dict(h: DiscountHistory) -> dict:
    return {
        "id": str(h.id),
        "sale_id": str(h.sale_id) if h.sale_id else None,
        "sale_number": h.sale_number,
        "discount_source": h.discount_source.value if h.discount_source else None,
        "promo_code": h.promo_code,
        "rule_name": h.rule_name,
        "product_id": str(h.product_id) if h.product_id else None,
        "product_name": h.product_name,
        "customer_id": str(h.customer_id) if h.customer_id else None,
        "customer_name": h.customer_name,
        "discount_type": h.discount_type,
        "discount_value": h.discount_value,
        "discount_amount": h.discount_amount,
        "original_amount": h.original_amount,
        "final_amount": h.final_amount,
        "reason": h.reason,
        "agent_code": h.agent_code,
        "agent_name": h.agent_name,
        "created_at": h.created_at.isoformat() if h.created_at else None
    }
