// Recherche produit : insensible aux accents/casse, classée par pertinence
export const foldText = (s) => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().trim();

const rank = (product, q) => {
  const name = foldText(product.name);
  if (!q) return 3;
  if (name.startsWith(q)) return 0;                                   // PARACETAMOL…
  if (name.split(/[\s/\-]+/).some((w) => w.startsWith(q))) return 1;  // HLE PARAFFINE…
  if (name.includes(q)) return 2;                                     // DIPARA…
  const code = foldText(product.barcode) + ' ' + foldText(product.internal_reference);
  if (code.includes(q)) return 2.5;
  return -1;
};

/** Filtre + tri des produits pour une saisie utilisateur. */
export const searchProducts = (products, query, { includeInactive = false } = {}) => {
  const q = foldText(query);
  return products
    .filter((p) => includeInactive || p.is_active !== false)
    .map((p) => ({ p, r: rank(p, q) }))
    .filter(({ r }) => r >= 0)
    .sort((a, b) => a.r - b.r || (b.p.stock > 0) - (a.p.stock > 0) || foldText(a.p.name).localeCompare(foldText(b.p.name)))
    .map(({ p }) => p);
};
