// Marge de référence : prix public = prix de cession × 1,4 (même valeur que backend/services/pricing.py)
export const DEFAULT_MARKUP = 1.4;

export const markupOf = (value) => (value && Number(value) > 0 ? Number(value) : DEFAULT_MARKUP);

export const estimatePurchasePrice = (price, purchasePrice) => {
  if (purchasePrice && purchasePrice > 0) return purchasePrice;
  return price && price > 0 ? price / DEFAULT_MARKUP : 0;
};
