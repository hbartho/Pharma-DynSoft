/**
 * Service centralisé pour gérer les opérations CRUD avec support offline
 * Ce service encapsule la logique de synchronisation pour toutes les pages
 */

import api from './api';
import {
  addItem,
  addItemLocal,
  getAllItems,
  updateItem,
  softDeleteItem,
  deleteItem,
  addLocalChange,
  bulkAddItems,
  clearStore,
  getDB,
} from './indexedDB';

// Store name to API endpoint mapping
const API_ENDPOINTS = {
  products: '/products',
  categories: '/categories',
  customers: '/customers',
  suppliers: '/suppliers',
  prescriptions: '/prescriptions',
  sales: '/sales',
};

/**
 * Load data from server or local IndexedDB
 * @param {string} storeName - Name of the store (products, customers, etc.)
 * @param {boolean} isOnline - Whether the app is online
 * @param {boolean} forceRefresh - Force refresh from server
 * @returns {Promise<Array>} - Array of items
 */
export const loadData = async (storeName, isOnline, forceRefresh = false) => {
  try {
    if (isOnline) {
      const endpoint = API_ENDPOINTS[storeName];
      if (!endpoint) {
        throw new Error(`Unknown store: ${storeName}`);
      }

      const headers = forceRefresh ? { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' } : {};
      const response = await api.get(endpoint, { headers });
      const serverData = response.data;

      // Clear local store if force refresh
      if (forceRefresh) {
        try {
          const db = await getDB();
          await db.clear(storeName);
        } catch (error) {
          console.warn(`Could not clear IndexedDB for ${storeName}:`, error);
        }
      }

      // Save to IndexedDB for offline access
      await bulkAddItems(storeName, serverData);

      return serverData;
    } else {
      // Offline: load from IndexedDB
      const localData = await getAllItems(storeName);
      return localData;
    }
  } catch (error) {
    console.error(`Error loading ${storeName}:`, error);
    // Fallback to local data on error
    const localData = await getAllItems(storeName);
    return localData;
  }
};

/**
 * Create a new item (online or offline)
 * @param {string} storeName - Name of the store
 * @param {Object} data - Item data
 * @param {boolean} isOnline - Whether the app is online
 * @returns {Promise<Object>} - Created item
 */
export const createItem = async (storeName, data, isOnline) => {
  const endpoint = API_ENDPOINTS[storeName];
  
  if (isOnline) {
    try {
      const response = await api.post(endpoint, data);
      const newItem = response.data;
      // Save to IndexedDB
      await addItem(storeName, newItem);
      return { success: true, data: newItem, offline: false };
    } catch (error) {
      console.error(`Error creating ${storeName}:`, error);
      throw error;
    }
  } else {
    // Offline: create locally with temp ID
    const tempId = crypto.randomUUID();
    const newItem = { ...data, id: tempId, _tempId: true };
    await addItemLocal(storeName, newItem);
    await addLocalChange(storeName.replace(/s$/, ''), 'create', newItem);
    return { success: true, data: newItem, offline: true };
  }
};

/**
 * Update an existing item (online or offline)
 * @param {string} storeName - Name of the store
 * @param {string} id - Item ID
 * @param {Object} data - Updated data
 * @param {boolean} isOnline - Whether the app is online
 * @returns {Promise<Object>} - Updated item
 */
export const updateItemData = async (storeName, id, data, isOnline) => {
  const endpoint = API_ENDPOINTS[storeName];
  
  if (isOnline) {
    try {
      const response = await api.put(`${endpoint}/${id}`, data);
      const updatedItem = response.data;
      // Update in IndexedDB
      await addItem(storeName, updatedItem);
      return { success: true, data: updatedItem, offline: false };
    } catch (error) {
      console.error(`Error updating ${storeName}:`, error);
      throw error;
    }
  } else {
    // Offline: update locally
    const updatedItem = { ...data, id };
    await updateItem(storeName, updatedItem);
    await addLocalChange(storeName.replace(/s$/, ''), 'update', updatedItem);
    return { success: true, data: updatedItem, offline: true };
  }
};

/**
 * Delete an item (online or offline)
 * @param {string} storeName - Name of the store
 * @param {string} id - Item ID
 * @param {boolean} isOnline - Whether the app is online
 * @returns {Promise<Object>} - Result
 */
export const deleteItemData = async (storeName, id, isOnline) => {
  const endpoint = API_ENDPOINTS[storeName];
  
  if (isOnline) {
    try {
      await api.delete(`${endpoint}/${id}`);
      // Remove from IndexedDB
      await deleteItem(storeName, id);
      return { success: true, offline: false };
    } catch (error) {
      console.error(`Error deleting ${storeName}:`, error);
      throw error;
    }
  } else {
    // Offline: soft delete locally
    await softDeleteItem(storeName, id);
    await addLocalChange(storeName.replace(/s$/, ''), 'delete', { id });
    return { success: true, offline: true };
  }
};

/**
 * Clear all browser and IndexedDB caches for a store
 * @param {string} storeName - Name of the store
 */
export const clearCaches = async (storeName) => {
  try {
    // Clear browser cache
    if ('caches' in window) {
      const cacheNames = await caches.keys();
      await Promise.all(cacheNames.map(name => caches.delete(name)));
    }
    // Clear IndexedDB store
    const db = await getDB();
    await db.clear(storeName);
  } catch (error) {
    console.warn(`Could not clear caches for ${storeName}:`, error);
  }
};

/**
 * Refresh data by clearing caches and reloading
 * @param {string} storeName - Name of the store
 * @param {boolean} isOnline - Whether the app is online
 * @returns {Promise<Array>} - Fresh data
 */
export const refreshData = async (storeName, isOnline) => {
  if (isOnline) {
    await clearCaches(storeName);
    return await loadData(storeName, true, true);
  } else {
    return await loadData(storeName, false);
  }
};
