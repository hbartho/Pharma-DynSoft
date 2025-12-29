import api from './api';
import {
  getLocalChanges,
  getPendingChanges,
  updateChangeStatus,
  clearSyncedChanges,
  addItem,
  bulkAddItems,
  clearStore,
  getAllItemsRaw,
  getUnsyncedItems,
  markItemAsSynced,
  setLastSyncTime,
  getLastSyncTime,
  getStoreCounts,
  SYNC_STORES
} from './indexedDB';

// Sync configuration
const SYNC_INTERVAL = 15 * 60 * 1000; // 15 minutes
const MAX_RETRY_COUNT = 3;

let syncIntervalId = null;
let syncInProgress = false;
let syncListeners = [];

// ============================================
// Sync Event System
// ============================================

export const addSyncListener = (callback) => {
  syncListeners.push(callback);
  return () => {
    syncListeners = syncListeners.filter(cb => cb !== callback);
  };
};

const notifyListeners = (event) => {
  syncListeners.forEach(cb => cb(event));
};

// ============================================
// API Endpoint Mapping
// ============================================

const API_ENDPOINTS = {
  products: '/products',
  categories: '/categories',
  customers: '/customers',
  suppliers: '/suppliers',
  prescriptions: '/prescriptions',
  sales: '/sales'
};

// ============================================
// Push Local Changes to Server
// ============================================

const pushChange = async (change) => {
  const { type, action, payload } = change;
  const endpoint = API_ENDPOINTS[type];
  
  if (!endpoint) {
    console.warn(`No endpoint configured for type: ${type}`);
    return { success: false, error: 'Unknown type' };
  }
  
  try {
    let response;
    
    switch (action) {
      case 'create':
        response = await api.post(endpoint, payload);
        break;
      case 'update':
        response = await api.put(`${endpoint}/${payload.id}`, payload);
        break;
      case 'delete':
        response = await api.delete(`${endpoint}/${payload.id}`);
        break;
      default:
        return { success: false, error: `Unknown action: ${action}` };
    }
    
    return { success: true, data: response.data };
  } catch (error) {
    const errorMessage = error.response?.data?.detail || error.message;
    console.error(`Failed to push ${action} ${type}:`, errorMessage);
    return { success: false, error: errorMessage };
  }
};

const pushAllChanges = async (onProgress = null) => {
  const pendingChanges = await getPendingChanges();
  
  if (pendingChanges.length === 0) {
    return { pushed: 0, failed: 0, errors: [] };
  }
  
  let pushed = 0;
  let failed = 0;
  const errors = [];
  
  for (let i = 0; i < pendingChanges.length; i++) {
    const change = pendingChanges[i];
    
    // Skip if max retries exceeded
    if (change.retryCount >= MAX_RETRY_COUNT) {
      continue;
    }
    
    await updateChangeStatus(change.id, 'syncing');
    
    if (onProgress) {
      onProgress({ current: i + 1, total: pendingChanges.length, change });
    }
    
    const result = await pushChange(change);
    
    if (result.success) {
      await updateChangeStatus(change.id, 'synced');
      pushed++;
    } else {
      await updateChangeStatus(change.id, 'error', result.error);
      failed++;
      errors.push({ change, error: result.error });
    }
  }
  
  // Clean up synced changes
  await clearSyncedChanges();
  
  return { pushed, failed, errors };
};

// ============================================
// Pull Data from Server
// ============================================

const pullCollection = async (storeName, forceFullSync = false) => {
  const endpoint = API_ENDPOINTS[storeName];
  
  if (!endpoint) {
    console.warn(`No endpoint configured for: ${storeName}`);
    return { success: false, count: 0 };
  }
  
  try {
    const response = await api.get(endpoint);
    const serverData = response.data;
    
    if (Array.isArray(serverData)) {
      if (forceFullSync) {
        // Clear and replace all data
        await clearStore(storeName);
      }
      
      // Bulk add items
      await bulkAddItems(storeName, serverData);
      
      return { success: true, count: serverData.length };
    }
    
    return { success: true, count: 0 };
  } catch (error) {
    console.error(`Failed to pull ${storeName}:`, error.message);
    return { success: false, count: 0, error: error.message };
  }
};

const pullAllCollections = async (forceFullSync = false, onProgress = null) => {
  const results = {};
  let totalPulled = 0;
  
  for (let i = 0; i < SYNC_STORES.length; i++) {
    const storeName = SYNC_STORES[i];
    
    if (onProgress) {
      onProgress({ current: i + 1, total: SYNC_STORES.length, store: storeName });
    }
    
    try {
      const result = await pullCollection(storeName, forceFullSync);
      results[storeName] = result;
      if (result.success) {
        totalPulled += result.count;
        await setLastSyncTime(storeName);
      }
    } catch (error) {
      results[storeName] = { success: false, error: error.message };
    }
  }
  
  return { results, totalPulled };
};

// ============================================
// Main Sync Function
// ============================================

export const syncData = async (options = {}) => {
  const {
    forceFullSync = false,
    onProgress = null,
    silent = false
  } = options;
  
  // Prevent concurrent syncs
  if (syncInProgress) {
    return { success: false, message: 'Sync already in progress' };
  }
  
  // Check if online
  if (!navigator.onLine) {
    return { success: false, message: 'Offline - sync skipped' };
  }
  
  syncInProgress = true;
  const startTime = Date.now();
  
  notifyListeners({ type: 'sync_start' });
  
  try {
    // Phase 1: Push local changes to server
    if (!silent) {
      notifyListeners({ type: 'push_start' });
    }
    
    const pushResults = await pushAllChanges((progress) => {
      notifyListeners({ type: 'push_progress', ...progress });
      if (onProgress) onProgress({ phase: 'push', ...progress });
    });
    
    if (!silent) {
      notifyListeners({ type: 'push_complete', results: pushResults });
    }
    
    // Phase 2: Pull latest data from server
    if (!silent) {
      notifyListeners({ type: 'pull_start' });
    }
    
    const pullResults = await pullAllCollections(forceFullSync, (progress) => {
      notifyListeners({ type: 'pull_progress', ...progress });
      if (onProgress) onProgress({ phase: 'pull', ...progress });
    });
    
    if (!silent) {
      notifyListeners({ type: 'pull_complete', results: pullResults });
    }
    
    // Update global sync time
    await setLastSyncTime('global');
    
    const duration = Date.now() - startTime;
    
    const result = {
      success: true,
      message: 'Sync completed',
      duration,
      pushed: pushResults.pushed,
      pushFailed: pushResults.failed,
      pulled: pullResults.totalPulled,
      timestamp: new Date().toISOString()
    };
    
    notifyListeners({ type: 'sync_complete', ...result });
    
    return result;
    
  } catch (error) {
    console.error('Sync error:', error);
    
    const result = {
      success: false,
      message: error.message,
      timestamp: new Date().toISOString()
    };
    
    notifyListeners({ type: 'sync_error', error: error.message });
    
    return result;
    
  } finally {
    syncInProgress = false;
  }
};

// ============================================
// Auto Sync (every 15 minutes)
// ============================================

export const startAutoSync = () => {
  if (syncIntervalId) {
    console.log('Auto sync already running');
    return;
  }
  
  console.log(`Starting auto sync every ${SYNC_INTERVAL / 60000} minutes`);
  
  // Initial sync after 30 seconds
  setTimeout(async () => {
    if (navigator.onLine) {
      await syncData({ silent: true });
    }
  }, 30000);
  
  // Regular sync every 15 minutes
  syncIntervalId = setInterval(async () => {
    if (navigator.onLine && !syncInProgress) {
      console.log('Auto sync triggered');
      await syncData({ silent: true });
    }
  }, SYNC_INTERVAL);
  
  return syncIntervalId;
};

export const stopAutoSync = () => {
  if (syncIntervalId) {
    clearInterval(syncIntervalId);
    syncIntervalId = null;
    console.log('Auto sync stopped');
  }
};

export const isAutoSyncRunning = () => {
  return syncIntervalId !== null;
};

// ============================================
// Sync Status & Statistics
// ============================================

export const getSyncStatus = async () => {
  const counts = await getStoreCounts();
  const pendingChanges = await getPendingChanges();
  const lastSyncTime = await getLastSyncTime('global');
  
  let totalUnsynced = 0;
  for (const store of Object.values(counts)) {
    totalUnsynced += store.unsynced;
  }
  
  return {
    isOnline: navigator.onLine,
    isSyncing: syncInProgress,
    lastSyncTime,
    pendingChanges: pendingChanges.length,
    unsyncedItems: totalUnsynced,
    storeCounts: counts,
    autoSyncRunning: isAutoSyncRunning()
  };
};

// ============================================
// Force Full Sync
// ============================================

export const forceFullSync = async () => {
  return await syncData({ forceFullSync: true });
};

// ============================================
// Sync Single Collection
// ============================================

export const syncCollection = async (storeName) => {
  if (!navigator.onLine) {
    return { success: false, message: 'Offline' };
  }
  
  try {
    const result = await pullCollection(storeName, true);
    if (result.success) {
      await setLastSyncTime(storeName);
    }
    return result;
  } catch (error) {
    return { success: false, error: error.message };
  }
};

// ============================================
// Export for backward compatibility
// ============================================

export const autoSync = startAutoSync;
