"""
Service de calcul du stock et des prix des produits - PostgreSQL Only
Agrège les données depuis les repositories PostgreSQL
Supporte les méthodes de valorisation: FIFO, LIFO, FEFO, CMP (Coût Moyen Pondéré)
"""
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum


class StockValuationMethod(str, Enum):
    FIFO = "fifo"           # First In First Out - Premier entré, premier sorti
    LIFO = "lifo"           # Last In First Out - Dernier entré, premier sorti
    FEFO = "fefo"           # First Expired First Out - Premier périmé, premier sorti
    WEIGHTED_AVERAGE = "weighted_average"  # Coût Moyen Pondéré (CMP/PMP)


def get_settings(tenant_id: str = None) -> dict:
    """Récupérer les paramètres du tenant depuis PostgreSQL"""
    from database.repositories import SettingsRepository
    repo = SettingsRepository()
    settings = repo.get_all()
    
    if not settings:
        return {
            "stock_valuation_method": "fefo",
            "default_min_stock": 10,
            "expiration_alert_days": 30
        }
    return settings


def get_product_stock_summary(product_id: str, tenant_id: str = None) -> Dict:
    """
    Calcule le résumé du stock d'un produit depuis les lots PostgreSQL
    
    Returns:
        Dict avec: total_stock, lots_count, nearest_expiration, etc.
    """
    from database.repositories_extended import StockLotRepository
    repo = StockLotRepository()
    
    # Récupérer les lots actifs du produit
    lots = repo.get_by_product_active(product_id)
    
    total_stock = 0
    lots_count = 0
    nearest_expiration = None
    expired_lots_count = 0
    near_expiration_lots_count = 0
    now = datetime.now(timezone.utc)
    expiration_threshold = now + timedelta(days=30)
    
    for lot in lots:
        quantity = lot.get("current_quantity", 0)
        total_stock += quantity
        lots_count += 1
        
        exp_date = lot.get("expiration_date")
        if exp_date:
            if isinstance(exp_date, str):
                exp_date = datetime.fromisoformat(exp_date)
            if exp_date.tzinfo is None:
                exp_date = exp_date.replace(tzinfo=timezone.utc)
            
            # Vérifier si expiré
            if exp_date <= now:
                expired_lots_count += 1
            elif exp_date <= expiration_threshold:
                near_expiration_lots_count += 1
            
            # Trouver la date de péremption la plus proche (non expirée)
            if exp_date > now:
                if nearest_expiration is None or exp_date < nearest_expiration:
                    nearest_expiration = exp_date
    
    return {
        "total_stock": total_stock,
        "lots_count": lots_count,
        "nearest_expiration": nearest_expiration,
        "expired_lots_count": expired_lots_count,
        "near_expiration_lots_count": near_expiration_lots_count
    }


def calculate_prices_by_method(lots: List[dict], method: str) -> Tuple[float, float, Optional[datetime]]:
    """
    Calcule les prix selon la méthode de valorisation choisie
    
    Args:
        lots: Liste des lots actifs avec current_quantity > 0
        method: Méthode de valorisation (fifo, lifo, fefo, weighted_average)
    
    Returns:
        Tuple (purchase_price, selling_price, reference_expiration_date)
    """
    if not lots:
        return 0, 0, None
    
    now = datetime.now(timezone.utc)
    
    # Filtrer les lots avec du stock
    active_lots = [l for l in lots if l.get("current_quantity", 0) > 0]
    if not active_lots:
        return 0, 0, None
    
    reference_lot = None
    reference_expiration = None
    
    if method == StockValuationMethod.FIFO.value:
        # FIFO: Premier entré (le plus ancien) - trié par date de création
        sorted_lots = sorted(active_lots, key=lambda x: x.get("created_at", "") or "")
        reference_lot = sorted_lots[0] if sorted_lots else None
        
    elif method == StockValuationMethod.LIFO.value:
        # LIFO: Dernier entré (le plus récent) - trié par date de création desc
        sorted_lots = sorted(active_lots, key=lambda x: x.get("created_at", "") or "", reverse=True)
        reference_lot = sorted_lots[0] if sorted_lots else None
        
    elif method == StockValuationMethod.FEFO.value:
        # FEFO: Premier périmé, premier sorti
        lots_with_expiration = [l for l in active_lots if l.get("expiration_date")]
        lots_without_expiration = [l for l in active_lots if not l.get("expiration_date")]
        
        if lots_with_expiration:
            sorted_lots = sorted(lots_with_expiration, key=lambda x: x.get("expiration_date", "") or "")
            for lot in sorted_lots:
                exp_date = lot.get("expiration_date")
                if exp_date:
                    if isinstance(exp_date, str):
                        exp_date = datetime.fromisoformat(exp_date)
                    if exp_date.tzinfo is None:
                        exp_date = exp_date.replace(tzinfo=timezone.utc)
                    if exp_date > now:
                        reference_lot = lot
                        reference_expiration = exp_date
                        break
            if not reference_lot and sorted_lots:
                reference_lot = sorted_lots[0]
        
        if not reference_lot and lots_without_expiration:
            sorted_lots = sorted(lots_without_expiration, key=lambda x: x.get("created_at", "") or "")
            reference_lot = sorted_lots[0]
            
    elif method == StockValuationMethod.WEIGHTED_AVERAGE.value:
        # Coût Moyen Pondéré: Moyenne des prix pondérée par les quantités
        total_purchase_value = 0
        total_selling_value = 0
        total_quantity = 0
        
        for lot in active_lots:
            qty = lot.get("current_quantity", 0)
            total_purchase_value += lot.get("purchase_price", 0) * qty
            total_selling_value += lot.get("selling_price", 0) * qty
            total_quantity += qty
        
        if total_quantity > 0:
            avg_purchase = round(total_purchase_value / total_quantity, 2)
            avg_selling = round(total_selling_value / total_quantity, 2)
            
            # Pour la date de péremption, utiliser FEFO (la plus proche)
            lots_with_exp = [l for l in active_lots if l.get("expiration_date")]
            if lots_with_exp:
                sorted_by_exp = sorted(lots_with_exp, key=lambda x: x.get("expiration_date", "") or "")
                for lot in sorted_by_exp:
                    exp_date = lot.get("expiration_date")
                    if exp_date:
                        if isinstance(exp_date, str):
                            exp_date = datetime.fromisoformat(exp_date)
                        if exp_date.tzinfo is None:
                            exp_date = exp_date.replace(tzinfo=timezone.utc)
                        if exp_date > now:
                            reference_expiration = exp_date
                            break
            
            return avg_purchase, avg_selling, reference_expiration
        
        return 0, 0, None
    
    # Extraire les prix du lot de référence
    if reference_lot:
        purchase_price = reference_lot.get("purchase_price", 0)
        selling_price = reference_lot.get("selling_price", 0)
        
        # Si pas encore définie, extraire la date de péremption
        if not reference_expiration:
            exp_date = reference_lot.get("expiration_date")
            if exp_date:
                if isinstance(exp_date, str):
                    exp_date = datetime.fromisoformat(exp_date)
                if exp_date.tzinfo is None:
                    exp_date = exp_date.replace(tzinfo=timezone.utc)
                reference_expiration = exp_date
        
        return purchase_price, selling_price, reference_expiration
    
    return 0, 0, None


def get_product_current_prices(product_id: str, tenant_id: str = None, method: str = None) -> Dict:
    """
    Récupère les prix actuels d'un produit selon la méthode de valorisation
    
    Args:
        product_id: ID du produit
        tenant_id: ID du tenant (unused, for compatibility)
        method: Méthode de valorisation (si None, récupère depuis settings)
    
    Returns:
        Dict avec: purchase_price, selling_price, expiration_date
    """
    from database.repositories_extended import StockLotRepository
    
    # Récupérer la méthode depuis les settings si non fournie
    if not method:
        settings = get_settings(tenant_id)
        method = settings.get("stock_valuation_method", "fefo")
    
    # Récupérer les lots actifs
    repo = StockLotRepository()
    lots = repo.get_by_product_active(product_id)
    
    if lots:
        purchase_price, selling_price, exp_date = calculate_prices_by_method(lots, method)
        return {
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "expiration_date": exp_date
        }
    
    return {
        "purchase_price": 0,
        "selling_price": 0,
        "expiration_date": None
    }


def get_product_min_stock(product_id: str, tenant_id: str = None, category_id: str = None) -> int:
    """
    Récupère le stock minimum pour un produit
    Priorité: 1. Config produit > 2. Config catégorie > 3. Paramètre global
    
    Args:
        product_id: ID du produit
        tenant_id: ID du tenant (unused, for compatibility)
        category_id: ID de la catégorie (optionnel)
    
    Returns:
        int: stock minimum
    """
    from database.repositories import CategoryRepository
    
    # 2. Vérifier si la catégorie a un stock minimum défini
    if category_id:
        cat_repo = CategoryRepository()
        category = cat_repo.get_by_id_str(category_id)
        if category and category.get("min_stock") is not None:
            return category.get("min_stock")
    
    # 3. Utiliser le paramètre global
    settings = get_settings(tenant_id)
    return settings.get("default_min_stock", 10)


def get_product_with_stock(product: dict, tenant_id: str = None, method: str = None) -> dict:
    """
    Enrichit un produit avec ses informations de stock et prix calculées
    selon la méthode de valorisation configurée
    
    Args:
        product: Le produit de base
        tenant_id: ID du tenant (unused, for compatibility)
        method: Méthode de valorisation (si None, récupère depuis settings)
    
    Returns:
        dict: Produit enrichi avec stock, prix, min_stock, expiration_date
    """
    product_id = product.get("id")
    category_id = product.get("category_id")
    
    # Récupérer la méthode depuis les settings si non fournie
    if not method:
        settings = get_settings(tenant_id)
        method = settings.get("stock_valuation_method", "fefo")
    
    # Récupérer le résumé du stock
    stock_summary = get_product_stock_summary(product_id, tenant_id)
    
    # Récupérer les prix selon la méthode de valorisation
    prices = get_product_current_prices(product_id, tenant_id, method)
    
    # Récupérer le stock minimum (produit > catégorie > global)
    min_stock = get_product_min_stock(product_id, tenant_id, category_id)
    
    # Enrichir le produit
    enriched_product = {**product}
    enriched_product["stock"] = stock_summary["total_stock"]
    enriched_product["purchase_price"] = prices["purchase_price"]
    enriched_product["price"] = prices["selling_price"]
    enriched_product["min_stock"] = min_stock
    
    exp_date = prices.get("expiration_date") or stock_summary.get("nearest_expiration")
    enriched_product["expiration_date"] = exp_date.isoformat() if exp_date else None
    enriched_product["lots_count"] = stock_summary["lots_count"]
    enriched_product["expired_lots_count"] = stock_summary["expired_lots_count"]
    
    return enriched_product
