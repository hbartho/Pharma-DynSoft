"""Historique des prix : enregistrement partagé (ventes, approvisionnements, gestion des prix)."""
import uuid
from typing import Optional

from database.models_tenant import PriceHistory, Product


def record_price_change(session, product: Product, prix_appro: Optional[float], prix_vente: Optional[float],
                        change_type: str, employee_code: str, reference_type: str = None,
                        reference_id=None, notes: str = None) -> Optional[PriceHistory]:
    """Ajoute une ligne d'historique si un prix change réellement, dans la transaction appelante."""
    avant_appro = float(product.purchase_price or 0)
    avant_vente = float(product.price or 0)
    new_appro = float(prix_appro) if prix_appro is not None else avant_appro
    new_vente = float(prix_vente) if prix_vente is not None else avant_vente
    if new_appro == avant_appro and new_vente == avant_vente:
        return None
    entry = PriceHistory(
        id=uuid.uuid4(),
        product_id=product.id,
        product_name=product.name,
        product_reference=getattr(product, "internal_reference", None),
        prix_appro=new_appro,
        prix_vente_prod=new_vente,
        prix_appro_avant=avant_appro,
        prix_vente_avant=avant_vente,
        change_type=change_type,
        reference_type=reference_type,
        reference_id=reference_id if isinstance(reference_id, uuid.UUID) or reference_id is None else uuid.UUID(str(reference_id)),
        notes=notes,
        created_by=employee_code,
    )
    session.add(entry)
    return entry


def price_history_to_dict(h: PriceHistory) -> dict:
    return {
        "id": str(h.id),
        "product_id": str(h.product_id),
        "product_name": h.product_name,
        "product_reference": h.product_reference,
        "prix_appro": h.prix_appro,
        "prix_vente_prod": h.prix_vente_prod,
        "prix_appro_avant": h.prix_appro_avant,
        "prix_vente_avant": h.prix_vente_avant,
        "date_maj_prix": h.created_at.isoformat() if h.created_at else None,
        "change_type": h.change_type,
        "reference_type": h.reference_type,
        "reference_id": str(h.reference_id) if h.reference_id else None,
        "notes": h.notes,
        "created_by": h.created_by,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }
