"""Normalisation de texte : noms de produits en MAJUSCULES sans accent."""
import re
import unicodedata


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def normalize_product_name(value) -> str:
    """paracétamol 500 mg  ->  PARACETAMOL 500 MG (espaces multiples réduits)."""
    if value is None:
        return value
    text = strip_accents(str(value)).upper()
    return re.sub(r"\s+", " ", text).strip()
