"""Règles de prix communes : coefficient de référence et estimations."""

# Marge de référence : prix public = prix de cession × 1,4
DEFAULT_MARKUP = 1.4


def estimate_purchase_price(price, purchase_price=None) -> float:
    """Prix de cession connu, sinon estimé depuis le prix public via le coefficient de référence."""
    if purchase_price and purchase_price > 0:
        return float(purchase_price)
    if price and price > 0:
        return float(price) / DEFAULT_MARKUP
    return 0.0


def default_selling_price(unit_price, current_price=None, coefficient=None) -> float:
    """Prix public par défaut d'une ligne d'appro sans prix saisi : prix actuel du produit, sinon cession × coefficient."""
    if current_price and current_price > 0:
        return float(current_price)
    coef = coefficient if coefficient and coefficient > 0 else DEFAULT_MARKUP
    return round(float(unit_price or 0) * coef)
