/**
 * Service de gestion des opérations hors-ligne
 * Permet de créer des ventes et autres opérations même sans connexion
 */

import { v4 as uuidv4 } from 'uuid';
import { 
  addLocalChange, 
  getLocalChanges, 
  updateChangeStatus,
  addItemLocal,
  getItem,
  updateItem,
  getAllItems
} from './indexedDB';
import api from './api';

// Clé pour les données temporaires en attente
const OFFLINE_SALES_KEY = 'offline_sales';
const OFFLINE_RETURNS_KEY = 'offline_returns';

/**
 * Créer une vente hors-ligne
 * La vente est sauvegardée localement et sera synchronisée au retour en ligne
 */
export const createOfflineSale = async (saleData, products) => {
  const saleId = `offline-sale-${uuidv4()}`;
  const saleNumber = `VNT-OFF-${Date.now().toString(36).toUpperCase()}`;
  
  // Enrichir les items avec les infos produits
  const enrichedItems = saleData.items.map(item => {
    const product = products.find(p => p.id === item.product_id);
    return {
      ...item,
      product_name: product?.name || 'Produit inconnu',
      unit_price: item.unit_price || product?.price || 0,
      subtotal: item.quantity * (item.unit_price || product?.price || 0)
    };
  });

  const offlineSale = {
    id: saleId,
    sale_number: saleNumber,
    items: enrichedItems,
    total: saleData.total,
    payment_method: saleData.payment_method,
    customer_id: saleData.customer_id || null,
    prescription_id: saleData.prescription_id || null,
    notes: saleData.notes || null,
    created_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  // Sauvegarder dans IndexedDB
  await addItemLocal('sales', offlineSale);

  // Ajouter à la queue de synchronisation
  await addLocalChange('sales', 'create', {
    ...saleData,
    items: enrichedItems,
    _offlineId: saleId
  });

  // Mettre à jour le stock local
  for (const item of saleData.items) {
    const product = await getItem('products', item.product_id);
    if (product) {
      const newStock = Math.max(0, (product.stock || 0) - item.quantity);
      await updateItem('products', { ...product, stock: newStock });
    }
  }

  return offlineSale;
};

/**
 * Créer un retour hors-ligne
 */
export const createOfflineReturn = async (returnData, sale) => {
  const returnId = `offline-return-${uuidv4()}`;
  const returnNumber = `RET-OFF-${Date.now().toString(36).toUpperCase()}`;

  const offlineReturn = {
    id: returnId,
    return_number: returnNumber,
    sale_id: returnData.sale_id,
    sale_number: sale?.sale_number,
    items: returnData.items,
    reason: returnData.reason,
    total_refund: returnData.items.reduce((sum, item) => sum + (item.price * item.quantity), 0),
    created_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  await addItemLocal('returns', offlineReturn);

  await addLocalChange('returns', 'create', {
    ...returnData,
    _offlineId: returnId
  });

  // Restaurer le stock local
  for (const item of returnData.items) {
    const product = await getItem('products', item.product_id);
    if (product) {
      const newStock = (product.stock || 0) + item.quantity;
      await updateItem('products', { ...product, stock: newStock });
    }
  }

  return offlineReturn;
};

/**
 * Créer un produit hors-ligne
 */
export const createOfflineProduct = async (productData) => {
  const productId = `offline-product-${uuidv4()}`;
  const internalRef = `PRD-OFF-${Date.now().toString(36).toUpperCase()}`;

  const offlineProduct = {
    ...productData,
    id: productId,
    internal_reference: productData.internal_reference || internalRef,
    stock: 0, // Les nouveaux produits commencent avec stock 0
    is_active: true,
    created_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  await addItemLocal('products', offlineProduct);
  await addLocalChange('products', 'create', {
    ...productData,
    _offlineId: productId
  });

  return offlineProduct;
};

/**
 * Créer un client hors-ligne
 */
export const createOfflineCustomer = async (customerData) => {
  const customerId = `offline-customer-${uuidv4()}`;

  const offlineCustomer = {
    ...customerData,
    id: customerId,
    created_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  await addItemLocal('customers', offlineCustomer);
  await addLocalChange('customers', 'create', {
    ...customerData,
    _offlineId: customerId
  });

  return offlineCustomer;
};

/**
 * Créer un fournisseur hors-ligne
 */
export const createOfflineSupplier = async (supplierData) => {
  const supplierId = `offline-supplier-${uuidv4()}`;

  const offlineSupplier = {
    ...supplierData,
    id: supplierId,
    is_active: true,
    created_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  await addItemLocal('suppliers', offlineSupplier);
  await addLocalChange('suppliers', 'create', {
    ...supplierData,
    _offlineId: supplierId
  });

  return offlineSupplier;
};

/**
 * Mettre à jour un élément hors-ligne
 */
export const updateOfflineItem = async (storeName, itemData) => {
  const existingItem = await getItem(storeName, itemData.id);
  
  if (!existingItem) {
    throw new Error(`Item not found in ${storeName}: ${itemData.id}`);
  }

  const updatedItem = {
    ...existingItem,
    ...itemData,
    updated_at: new Date().toISOString(),
    _offline: true,
    _synced: false,
    _pendingSync: true
  };

  await updateItem(storeName, updatedItem);
  await addLocalChange(storeName, 'update', itemData);

  return updatedItem;
};

/**
 * Supprimer un élément hors-ligne (soft delete)
 */
export const deleteOfflineItem = async (storeName, itemId) => {
  const existingItem = await getItem(storeName, itemId);
  
  if (!existingItem) {
    console.warn(`Item not found in ${storeName}: ${itemId}`);
    return null;
  }

  const deletedItem = {
    ...existingItem,
    _deleted: true,
    _offline: true,
    _synced: false,
    _pendingSync: true,
    deleted_at: new Date().toISOString()
  };

  await updateItem(storeName, deletedItem);
  await addLocalChange(storeName, 'delete', { id: itemId });

  return deletedItem;
};

/**
 * Vérifier si on est en mode hors-ligne
 */
export const isOffline = () => !navigator.onLine;

/**
 * Obtenir les opérations en attente de synchronisation
 */
export const getPendingOperations = async () => {
  const changes = await getLocalChanges('pending');
  return {
    total: changes.length,
    sales: changes.filter(c => c.type === 'sales').length,
    returns: changes.filter(c => c.type === 'returns').length,
    products: changes.filter(c => c.type === 'products').length,
    customers: changes.filter(c => c.type === 'customers').length,
    suppliers: changes.filter(c => c.type === 'suppliers').length,
    changes
  };
};

/**
 * Synchroniser une opération spécifique
 */
export const syncOperation = async (change) => {
  const { type, action, payload } = change;
  
  const endpoints = {
    sales: '/sales',
    returns: '/returns',
    products: '/products',
    customers: '/customers',
    suppliers: '/suppliers',
    categories: '/categories',
    units: '/units',
    supplies: '/supplies',
    prescriptions: '/prescriptions',
  };

  const endpoint = endpoints[type];
  if (!endpoint) {
    throw new Error(`Type d'opération non supporté: ${type}`);
  }

  try {
    let response;
    
    // Nettoyer le payload des champs offline
    const cleanPayload = { ...payload };
    delete cleanPayload._offlineId;
    delete cleanPayload._offline;
    delete cleanPayload._synced;
    delete cleanPayload._pendingSync;

    switch (action) {
      case 'create':
        response = await api.post(endpoint, cleanPayload);
        break;
      case 'update':
        response = await api.put(`${endpoint}/${payload.id}`, cleanPayload);
        break;
      case 'delete':
        response = await api.delete(`${endpoint}/${payload.id}`);
        break;
      default:
        throw new Error(`Action non supportée: ${action}`);
    }

    // Mettre à jour le statut
    await updateChangeStatus(change.id, 'synced');

    // Si c'était une création offline, mettre à jour l'ID local avec l'ID serveur
    if (action === 'create' && payload._offlineId && response.data?.id) {
      // Supprimer l'ancien enregistrement offline et le remplacer par le nouveau
      const store = type === 'sales' ? 'sales' : type;
      const oldItem = await getItem(store, payload._offlineId);
      if (oldItem) {
        await updateItem(store, {
          ...oldItem,
          ...response.data,
          _synced: true,
          _pendingSync: false,
          _offline: false
        });
      }
    }

    return { success: true, data: response.data };
  } catch (error) {
    await updateChangeStatus(change.id, 'error', error.message);
    return { success: false, error: error.message };
  }
};

/**
 * Synchroniser toutes les opérations en attente
 */
export const syncAllPendingOperations = async (onProgress) => {
  const pending = await getLocalChanges('pending');
  
  if (pending.length === 0) {
    return { synced: 0, failed: 0, errors: [] };
  }

  let synced = 0;
  let failed = 0;
  const errors = [];

  for (let i = 0; i < pending.length; i++) {
    const change = pending[i];
    
    if (onProgress) {
      onProgress({
        current: i + 1,
        total: pending.length,
        type: change.type,
        action: change.action
      });
    }

    const result = await syncOperation(change);
    
    if (result.success) {
      synced++;
    } else {
      failed++;
      errors.push({ change, error: result.error });
    }
  }

  return { synced, failed, errors };
};

/**
 * Écouter les messages du Service Worker
 */
export const initOfflineListener = (onQueuedRequest) => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      const { type, request } = event.data || {};
      
      if (type === 'OFFLINE_REQUEST_QUEUED' && onQueuedRequest) {
        onQueuedRequest(request);
      }
      
      if (type === 'BACKGROUND_SYNC_TRIGGERED') {
        // Déclencher la synchronisation
        syncAllPendingOperations();
      }
    });
  }
};

/**
 * Demander une synchronisation en arrière-plan
 */
export const requestBackgroundSync = async () => {
  if ('serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype) {
    try {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-pending-changes');
      return true;
    } catch (error) {
      console.error('Background sync registration failed:', error);
      return false;
    }
  }
  return false;
};

export default {
  createOfflineSale,
  createOfflineReturn,
  createOfflineProduct,
  createOfflineCustomer,
  createOfflineSupplier,
  updateOfflineItem,
  deleteOfflineItem,
  isOffline,
  getPendingOperations,
  syncOperation,
  syncAllPendingOperations,
  initOfflineListener,
  requestBackgroundSync
};
