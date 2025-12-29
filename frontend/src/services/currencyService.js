/**
 * Service de gestion des devises et formatage monétaire
 */

// Symboles des devises
const CURRENCY_SYMBOLS = {
  USD: '$',
  CAD: '$ CAD',
  EUR: '€',
  XOF: 'FCFA',
  GNF: 'GNF',
};

// Noms complets des devises
const CURRENCY_NAMES = {
  USD: 'Dollar US',
  CAD: 'Dollar Canadien',
  EUR: 'Euro',
  XOF: 'Franc CFA',
  GNF: 'Franc Guinéen',
};

// Position du symbole (avant ou après le montant)
const CURRENCY_POSITION = {
  USD: 'before',
  CAD: 'after',
  EUR: 'after',
  XOF: 'after',
  GNF: 'after',
};

// Nombre de décimales par devise
const CURRENCY_DECIMALS = {
  USD: 2,
  CAD: 2,
  EUR: 2,
  XOF: 0, // FCFA n'a pas de centimes
  GNF: 0, // GNF n'a pas de centimes
};

/**
 * Formate un montant selon la devise
 * @param {number} amount - Le montant à formater
 * @param {string} currency - Le code de la devise (USD, EUR, etc.)
 * @returns {string} - Le montant formaté avec le symbole
 */
export const formatCurrency = (amount, currency = 'EUR') => {
  const symbol = CURRENCY_SYMBOLS[currency] || currency;
  const decimals = CURRENCY_DECIMALS[currency] ?? 2;
  const position = CURRENCY_POSITION[currency] || 'after';
  
  const formattedAmount = amount.toLocaleString('fr-FR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  
  if (position === 'before') {
    return `${symbol}${formattedAmount}`;
  }
  return `${formattedAmount} ${symbol}`;
};

/**
 * Obtient le symbole d'une devise
 * @param {string} currency - Le code de la devise
 * @returns {string} - Le symbole
 */
export const getCurrencySymbol = (currency = 'EUR') => {
  return CURRENCY_SYMBOLS[currency] || currency;
};

/**
 * Obtient le nom complet d'une devise
 * @param {string} currency - Le code de la devise
 * @returns {string} - Le nom complet
 */
export const getCurrencyName = (currency = 'EUR') => {
  return CURRENCY_NAMES[currency] || currency;
};

/**
 * Obtient le nombre de décimales d'une devise
 * @param {string} currency - Le code de la devise
 * @returns {number} - Le nombre de décimales
 */
export const getCurrencyDecimals = (currency = 'EUR') => {
  return CURRENCY_DECIMALS[currency] ?? 2;
};

export default {
  formatCurrency,
  getCurrencySymbol,
  getCurrencyName,
  getCurrencyDecimals,
  CURRENCY_SYMBOLS,
  CURRENCY_NAMES,
};
