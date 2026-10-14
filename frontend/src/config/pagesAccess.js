// Configuration des accès par page : liste des pages et défauts par rôle.

export const PAGES = [
  { key: '/dashboard', label: 'Tableau de bord', group: 'Général' },
  { key: '/sales', label: 'Ventes', group: 'Opérations' },
  { key: '/supplies', label: 'Approvisionnements', group: 'Opérations' },
  { key: '/customers', label: 'Clients', group: 'Opérations' },
  { key: '/suppliers', label: 'Fournisseurs', group: 'Opérations' },
  { key: '/products', label: 'Produits', group: 'Stocks' },
  { key: '/stock-movements', label: 'Mouvements', group: 'Stocks' },
  { key: '/inventory', label: 'Inventaire', group: 'Stocks' },
  { key: '/stock-losses', label: 'Pertes', group: 'Stocks' },
  { key: '/reports', label: 'Rapports', group: 'Finances' },
  { key: '/debts', label: 'Dettes Clients', group: 'Finances' },
  { key: '/supplier-debts', label: 'Solde Fournisseurs', group: 'Finances' },
  { key: '/promo-codes', label: 'Codes Promo', group: 'Rabais' },
  { key: '/discount-rules', label: 'Règles de rabais', group: 'Rabais' },
  { key: '/discount-history', label: 'Historique rabais', group: 'Rabais' },
  { key: '/shift-schedules', label: 'Planification Shifts', group: 'Administration' },
  { key: '/shifts', label: 'Historique Shifts', group: 'Administration' },
  { key: '/price-management', label: 'Gestion des Prix', group: 'Administration' },
  { key: '/payment-methods', label: 'Modes de paiement', group: 'Administration' },
  { key: '/users', label: 'Utilisateurs', group: 'Administration' },
  { key: '/settings', label: 'Paramètres', group: 'Administration' },
];

export const ROLE_DEFAULTS = {
  admin: PAGES.map(p => p.key),
  pharmacien: [
    '/dashboard', '/sales', '/supplies', '/customers', '/suppliers',
    '/products', '/stock-movements', '/stock-losses', '/reports',
  ],
  caissier: [
    '/dashboard', '/sales', '/supplies', '/customers', '/stock-losses',
  ],
};

export const getDefaultPermissions = (role) => [...(ROLE_DEFAULTS[role] || ROLE_DEFAULTS.caissier)];

export const getUserPermissions = (user) => {
  if (!user) return [];
  if (Array.isArray(user.permissions) && user.permissions.length > 0) {
    return user.permissions;
  }
  return getDefaultPermissions(user.role);
};

export const hasPageAccess = (user, path) => {
  if (!user) return false;
  if (user.role === 'super_admin') return true;
  return getUserPermissions(user).includes(path);
};

export const firstAccessiblePath = (user) => {
  const perms = getUserPermissions(user);
  const ordered = PAGES.map(p => p.key);
  return ordered.find(k => perms.includes(k)) || null;
};
