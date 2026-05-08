/**
 * Service de gestion des devises pour l'application
 */

// Symboles des devises
const CURRENCY_SYMBOLS = {
  EUR: '€',
  USD: '$',
  CAD: '$ CAD',
  XOF: 'FCFA',
  GNF: 'GNF',
};

// Noms des devises
const CURRENCY_NAMES = {
  EUR: 'Euro',
  USD: 'Dollar US',
  CAD: 'Dollar CAD',
  XOF: 'Franc CFA',
  GNF: 'Franc Guinéen',
};

// Nombre de décimales par devise
const CURRENCY_DECIMALS = {
  EUR: 2,
  USD: 2,
  CAD: 2,
  XOF: 0,
  GNF: 0,
};

/**
 * Obtient le nombre de décimales pour une devise
 * @param {string} currency - Code de la devise
 * @returns {number} Nombre de décimales (0-2)
 */
const getCurrencyDecimals = (currency) => {
  return CURRENCY_DECIMALS[currency] ?? 2;
};

/**
 * Formate un montant avec le bon nombre de décimales selon la devise
 * - Maximum 2 décimales pour EUR, USD, CAD
 * - 0 décimales pour GNF, XOF (pas de centimes)
 * 
 * @param {number} amount - Le montant à formater
 * @param {string} currency - Le code de la devise (EUR, USD, etc.)
 * @returns {string} Le montant formaté avec le symbole de la devise
 */
const formatCurrency = (amount, currency = 'GNF') => {
  const symbol = CURRENCY_SYMBOLS[currency] || currency;
  const decimals = getCurrencyDecimals(currency);
  
  // Arrondir le montant selon le nombre de décimales de la devise
  const roundedAmount = Math.round(amount * Math.pow(10, decimals)) / Math.pow(10, decimals);
  
  const formatted = roundedAmount.toLocaleString('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
  
  return `${formatted} ${symbol}`;
};

/**
 * Arrondit un montant à 2 décimales maximum
 * @param {number} amount - Le montant à arrondir
 * @returns {number} Le montant arrondi
 */
const roundAmount = (amount) => {
  return Math.round((amount || 0) * 100) / 100;
};

/**
 * Obtient le symbole d'une devise
 * @param {string} currency - Code de la devise
 * @returns {string} Symbole de la devise
 */
const getCurrencySymbol = (currency) => {
  return CURRENCY_SYMBOLS[currency] || currency;
};

export {
  formatCurrency,
  roundAmount,
  getCurrencySymbol,
  getCurrencyDecimals,
  CURRENCY_SYMBOLS,
  CURRENCY_NAMES,
  CURRENCY_DECIMALS,
};
