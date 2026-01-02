/**
 * Service des opérations offline pour DynSoft Pharma
 * Gère les opérations CRUD en mode hors ligne avec queue de synchronisation
 */

import { v4 as uuidv4 } from 'uuid';
import {
  getDB,
  addItem,
  addItemLocal,
  getItem,
  getAllItems,
  updateItem,
  softDeleteItem,
  addLocalChange,
  getPendingChanges,
  bulkAddItems,
  clearStore
} from './indexedDB';
import api from './api';

// ============================================
// Configuration
// ============================================

const OFFLINE_ENABLED_STORES = [
  'products',
  'categories',
  'customers',
  'suppliers',
  'sales',
  'supplies',
  'returns',
  'units',
  'prescriptions'
];

const API_ENDPOINTS = {
  products: '/products',
  categories: '/categories',
  customers: '/customers',
  suppliers: '/suppliers',
  sales: '/sales',
  supplies: '/supplies',
  returns: '/returns',
  units: '/units',
  prescriptions: '/prescriptions'
};

// ============================================
// Check if offline mode is active
// ============================================

export const isOffline = () => !navigator.onLine;

// ============================================
// Generic Offline CRUD Operations
// ============================================

/**
 * Récupérer tous les éléments (online: API, offline: IndexedDB)
 */
export const getAll = async (storeName) => {
  if (!OFFLINE_ENABLED_STORES.includes(storeName)) {
    throw new Error(`Store ${storeName} not configured for offline mode`);
  }

  const endpoint = API_ENDPOINTS[storeName];

  if (isOffline()) {
    console.log(`[Offline] Getting ${storeName} from IndexedDB`);
    return await getAllItems(storeName);
  }

  try {
    const response = await api.get(endpoint);
    const data = response.data;
    
    // Cache les données dans IndexedDB
    if (Array.isArray(data)) {
      await bulkAddItems(storeName, data);
    }
    
    return data;
  } catch (error) {
    console.warn(`[Offline] API failed, falling back to IndexedDB for ${storeName}`);
    return await getAllItems(storeName);
  }
};

/**
 * Récupérer un élément par ID
 */
export const getById = async (storeName, id) => {
  if (!OFFLINE_ENABLED_STORES.includes(storeName)) {
    throw new Error(`Store ${storeName} not configured for offline mode`);
  }

  const endpoint = API_ENDPOINTS[storeName];

  if (isOffline()) {
    console.log(`[Offline] Getting ${storeName}/${id} from IndexedDB`);
    return await getItem(storeName, id);
  }

  try {
    const response = await api.get(`${endpoint}/${id}`);
    const data = response.data;
    
    // Cache dans IndexedDB
    await addItem(storeName, data);
    
    return data;
  } catch (error) {
    console.warn(`[Offline] API failed, falling back to IndexedDB for ${storeName}/${id}`);
    return await getItem(storeName, id);
  }
};

/**
 * Créer un élément (online: API + cache, offline: queue + local)
 */
export const create = async (storeName, data, options = {}) => {
  if (!OFFLINE_ENABLED_STORES.includes(storeName)) {
    throw new Error(`Store ${storeName} not configured for offline mode`);
  }

  const endpoint = API_ENDPOINTS[storeName];
  
  // Générer un ID local si pas présent
  const itemWithId = {
    ...data,
    id: data.id || uuidv4(),
    _createdOffline: isOffline(),
    _createdAt: new Date().toISOString()
  };

  if (isOffline()) {
    console.log(`[Offline] Creating ${storeName} locally`);
    
    // Sauvegarder localement
    await addItemLocal(storeName, itemWithId);
    
    // Ajouter à la queue de synchronisation
    await addLocalChange(storeName, 'create', itemWithId);
    
    return { 
      ...itemWithId, 
      _offline: true,
      _pendingSync: true 
    };
  }

  try {
    const response = await api.post(endpoint, data);
    const savedData = response.data;
    
    // Cache dans IndexedDB
    await addItem(storeName, savedData);
    
    return savedData;
  } catch (error) {
    if (options.fallbackToOffline !== false) {
      console.warn(`[Offline] API failed, saving ${storeName} locally`);
      
      await addItemLocal(storeName, itemWithId);
      await addLocalChange(storeName, 'create', itemWithId);
      
      return { 
        ...itemWithId, 
        _offline: true,
        _pendingSync: true 
      };
    }
    throw error;
  }
};

/**
 * Mettre à jour un élément
 */
export const update = async (storeName, id, data, options = {}) => {
  if (!OFFLINE_ENABLED_STORES.includes(storeName)) {
    throw new Error(`Store ${storeName} not configured for offline mode`);
  }

  const endpoint = API_ENDPOINTS[storeName];
  
  const itemWithMeta = {
    ...data,
    id,
    _updatedOffline: isOffline(),
    _updatedAt: new Date().toISOString()
  };

  if (isOffline()) {
    console.log(`[Offline] Updating ${storeName}/${id} locally`);
    
    await updateItem(storeName, itemWithMeta);
    await addLocalChange(storeName, 'update', itemWithMeta);
    
    return { 
      ...itemWithMeta, 
      _offline: true,
      _pendingSync: true 
    };
  }

  try {
    const response = await api.put(`${endpoint}/${id}`, data);
    const savedData = response.data;
    
    await addItem(storeName, savedData);
    
    return savedData;
  } catch (error) {
    if (options.fallbackToOffline !== false) {
      console.warn(`[Offline] API failed, updating ${storeName}/${id} locally`);
      
      await updateItem(storeName, itemWithMeta);
      await addLocalChange(storeName, 'update', itemWithMeta);
      
      return { 
        ...itemWithMeta, 
        _offline: true,
        _pendingSync: true 
      };
    }
    throw error;
  }
};

/**
 * Supprimer un élément
 */
export const remove = async (storeName, id, options = {}) => {
  if (!OFFLINE_ENABLED_STORES.includes(storeName)) {
    throw new Error(`Store ${storeName} not configured for offline mode`);
  }

  const endpoint = API_ENDPOINTS[storeName];

  if (isOffline()) {
    console.log(`[Offline] Deleting ${storeName}/${id} locally`);
    
    await softDeleteItem(storeName, id);
    await addLocalChange(storeName, 'delete', { id });
    
    return { success: true, _offline: true, _pendingSync: true };
  }

  try {
    await api.delete(`${endpoint}/${id}`);
    
    // Supprimer du cache local
    const db = await getDB();
    await db.delete(storeName, id);
    
    return { success: true };
  } catch (error) {
    if (options.fallbackToOffline !== false) {
      console.warn(`[Offline] API failed, deleting ${storeName}/${id} locally`);
      
      await softDeleteItem(storeName, id);
      await addLocalChange(storeName, 'delete', { id });
      
      return { success: true, _offline: true, _pendingSync: true };
    }
    throw error;
  }
};

// ============================================
// Opérations spécifiques aux ventes (offline)
// ============================================

/**
 * Créer une vente en mode offline
 */
export const createSaleOffline = async (saleData, employeeCode) => {
  const saleId = uuidv4();
  const saleNumber = `VNT-${saleId.substring(0, 8).toUpperCase()}`;
  
  const sale = {
    ...saleData,
    id: saleId,
    sale_number: saleNumber,
    created_by: employeeCode,
    created_at: new Date().toISOString(),
    _createdOffline: true,
    _pendingSync: true
  };

  // Sauvegarder la vente localement
  await addItemLocal('sales', sale);
  
  // Mettre à jour le stock local des produits
  for (const item of saleData.items || []) {
    const product = await getItem('products', item.product_id);
    if (product) {
      const updatedProduct = {
        ...product,
        quantity_in_stock: Math.max(0, (product.quantity_in_stock || 0) - item.quantity),
        _updatedOffline: true
      };
      await updateItem('products', updatedProduct);
    }
  }
  
  // Ajouter à la queue de synchronisation
  await addLocalChange('sales', 'create', sale);
  
  return sale;
};

/**
 * Créer un retour en mode offline
 */
export const createReturnOffline = async (returnData, employeeCode) => {
  const returnId = uuidv4();
  const returnNumber = `RET-${returnId.substring(0, 8).toUpperCase()}`;
  
  const returnRecord = {
    ...returnData,
    id: returnId,
    return_number: returnNumber,
    created_by: employeeCode,
    created_at: new Date().toISOString(),
    _createdOffline: true,
    _pendingSync: true
  };

  // Sauvegarder le retour localement
  await addItemLocal('returns', returnRecord);
  
  // Mettre à jour le stock local des produits (ajouter les quantités retournées)
  for (const item of returnData.items || []) {
    const product = await getItem('products', item.product_id);
    if (product) {
      const updatedProduct = {
        ...product,
        quantity_in_stock: (product.quantity_in_stock || 0) + item.quantity,
        _updatedOffline: true
      };
      await updateItem('products', updatedProduct);
    }
  }
  
  // Ajouter à la queue de synchronisation
  await addLocalChange('returns', 'create', returnRecord);
  
  return returnRecord;
};

/**
 * Créer un approvisionnement en mode offline
 */
export const createSupplyOffline = async (supplyData, employeeCode) => {
  const supplyId = uuidv4();
  
  const supply = {
    ...supplyData,
    id: supplyId,
    is_validated: false,
    created_by: employeeCode,
    created_at: new Date().toISOString(),
    _createdOffline: true,
    _pendingSync: true
  };

  // Sauvegarder l'approvisionnement localement
  await addItemLocal('supplies', supply);
  
  // Ajouter à la queue de synchronisation
  await addLocalChange('supplies', 'create', supply);
  
  return supply;
};

// ============================================
// Statistiques offline
// ============================================

export const getOfflineStats = async () => {
  const pendingChanges = await getPendingChanges();
  
  const stats = {
    totalPending: pendingChanges.length,
    byType: {},
    byAction: {}
  };
  
  for (const change of pendingChanges) {
    // Par type
    stats.byType[change.type] = (stats.byType[change.type] || 0) + 1;
    // Par action
    stats.byAction[change.action] = (stats.byAction[change.action] || 0) + 1;
  }
  
  return stats;
};

// ============================================
// Préchargement des données pour le mode offline
// ============================================

export const preloadDataForOffline = async (onProgress = null) => {
  const stores = ['products', 'categories', 'customers', 'suppliers', 'units'];
  const results = {};
  
  for (let i = 0; i < stores.length; i++) {
    const store = stores[i];
    
    if (onProgress) {
      onProgress({ current: i + 1, total: stores.length, store });
    }
    
    try {
      const endpoint = API_ENDPOINTS[store];
      const response = await api.get(endpoint);
      const data = response.data;
      
      if (Array.isArray(data)) {
        await clearStore(store);
        await bulkAddItems(store, data);
        results[store] = { success: true, count: data.length };
      } else {
        results[store] = { success: true, count: 0 };
      }
    } catch (error) {
      results[store] = { success: false, error: error.message };
    }
  }
  
  return results;
};

export default {
  isOffline,
  getAll,
  getById,
  create,
  update,
  remove,
  createSaleOffline,
  createReturnOffline,
  createSupplyOffline,
  getOfflineStats,
  preloadDataForOffline
};
