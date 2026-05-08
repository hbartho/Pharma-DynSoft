import { openDB } from 'idb';

const DB_NAME = 'DynSoftPharmaDB';
const DB_VERSION = 3; // Increment version for new stores

let dbInstance = null;

// All collections that need to be synced
export const SYNC_STORES = [
  'products',
  'categories', 
  'sales',
  'customers',
  'suppliers',
  'prescriptions',
  'supplies',
  'returns',
  'units',
  'settings'
];

export const initDB = async () => {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion, newVersion) {
      // Products store
      if (!db.objectStoreNames.contains('products')) {
        const store = db.createObjectStore('products', { keyPath: 'id' });
        store.createIndex('updated_at', 'updated_at');
        store.createIndex('synced', 'synced');
      }
      
      // Categories store
      if (!db.objectStoreNames.contains('categories')) {
        const store = db.createObjectStore('categories', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Sales store
      if (!db.objectStoreNames.contains('sales')) {
        const store = db.createObjectStore('sales', { keyPath: 'id' });
        store.createIndex('created_at', 'created_at');
        store.createIndex('synced', 'synced');
      }
      
      // Customers store
      if (!db.objectStoreNames.contains('customers')) {
        const store = db.createObjectStore('customers', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Suppliers store
      if (!db.objectStoreNames.contains('suppliers')) {
        const store = db.createObjectStore('suppliers', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Prescriptions store
      if (!db.objectStoreNames.contains('prescriptions')) {
        const store = db.createObjectStore('prescriptions', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Supplies store (Approvisionnements)
      if (!db.objectStoreNames.contains('supplies')) {
        const store = db.createObjectStore('supplies', { keyPath: 'id' });
        store.createIndex('created_at', 'created_at');
        store.createIndex('synced', 'synced');
        store.createIndex('is_validated', 'is_validated');
      }
      
      // Returns store (Retours)
      if (!db.objectStoreNames.contains('returns')) {
        const store = db.createObjectStore('returns', { keyPath: 'id' });
        store.createIndex('created_at', 'created_at');
        store.createIndex('synced', 'synced');
        store.createIndex('sale_id', 'sale_id');
      }
      
      // Units store (Unités)
      if (!db.objectStoreNames.contains('units')) {
        const store = db.createObjectStore('units', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Settings store
      if (!db.objectStoreNames.contains('settings')) {
        const store = db.createObjectStore('settings', { keyPath: 'id' });
        store.createIndex('synced', 'synced');
      }
      
      // Local changes queue - for offline modifications
      if (!db.objectStoreNames.contains('local_changes')) {
        const store = db.createObjectStore('local_changes', { keyPath: 'id', autoIncrement: true });
        store.createIndex('timestamp', 'timestamp');
        store.createIndex('type', 'type');
        store.createIndex('status', 'status');
      }
      
      // Sync metadata - track last sync times
      if (!db.objectStoreNames.contains('sync_meta')) {
        db.createObjectStore('sync_meta', { keyPath: 'key' });
      }
      
      // User data
      if (!db.objectStoreNames.contains('user')) {
        db.createObjectStore('user', { keyPath: 'key' });
      }
    },
  });

  return dbInstance;
};

export const getDB = async () => {
  if (!dbInstance) {
    await initDB();
  }
  return dbInstance;
};

// ============================================
// Generic CRUD operations
// ============================================

export const addItem = async (storeName, item) => {
  const db = await getDB();
  // Add sync metadata
  const itemWithMeta = {
    ...item,
    _localUpdatedAt: new Date().toISOString(),
    _synced: true // Mark as synced if coming from server
  };
  await db.put(storeName, itemWithMeta);
  return itemWithMeta;
};

export const addItemLocal = async (storeName, item) => {
  const db = await getDB();
  // Add sync metadata - mark as not synced
  const itemWithMeta = {
    ...item,
    _localUpdatedAt: new Date().toISOString(),
    _synced: false
  };
  await db.put(storeName, itemWithMeta);
  return itemWithMeta;
};

export const getItem = async (storeName, id) => {
  const db = await getDB();
  return await db.get(storeName, id);
};

export const getAllItems = async (storeName) => {
  const db = await getDB();
  const items = await db.getAll(storeName);
  // Filter out deleted items for display
  return items.filter(item => !item._deleted);
};

export const getAllItemsRaw = async (storeName) => {
  const db = await getDB();
  return await db.getAll(storeName);
};

export const updateItem = async (storeName, item) => {
  const db = await getDB();
  const itemWithMeta = {
    ...item,
    _localUpdatedAt: new Date().toISOString(),
    _synced: false
  };
  await db.put(storeName, itemWithMeta);
  return itemWithMeta;
};

export const deleteItem = async (storeName, id) => {
  const db = await getDB();
  await db.delete(storeName, id);
};

export const softDeleteItem = async (storeName, id) => {
  const db = await getDB();
  const item = await db.get(storeName, id);
  if (item) {
    const deletedItem = {
      ...item,
      _deleted: true,
      _localUpdatedAt: new Date().toISOString(),
      _synced: false
    };
    await db.put(storeName, deletedItem);
    return deletedItem;
  }
  return null;
};

export const clearStore = async (storeName) => {
  const db = await getDB();
  const tx = db.transaction(storeName, 'readwrite');
  await tx.objectStore(storeName).clear();
};

export const bulkAddItems = async (storeName, items) => {
  const db = await getDB();
  const tx = db.transaction(storeName, 'readwrite');
  const store = tx.objectStore(storeName);
  
  for (const item of items) {
    const itemWithMeta = {
      ...item,
      _localUpdatedAt: new Date().toISOString(),
      _synced: true
    };
    await store.put(itemWithMeta);
  }
  
  await tx.done;
};

// ============================================
// Local changes tracking (offline queue)
// ============================================

export const addLocalChange = async (type, action, payload) => {
  const db = await getDB();
  const change = {
    type,        // 'product', 'sale', 'customer', etc.
    action,      // 'create', 'update', 'delete'
    payload,     // The data
    timestamp: new Date().toISOString(),
    status: 'pending', // 'pending', 'syncing', 'synced', 'error'
    retryCount: 0
  };
  const id = await db.add('local_changes', change);
  return { ...change, id };
};

export const getLocalChanges = async (status = null) => {
  const db = await getDB();
  const allChanges = await db.getAll('local_changes');
  if (status) {
    return allChanges.filter(c => c.status === status);
  }
  return allChanges;
};

export const getPendingChanges = async () => {
  return await getLocalChanges('pending');
};

export const updateChangeStatus = async (id, status, error = null) => {
  const db = await getDB();
  const change = await db.get('local_changes', id);
  if (change) {
    change.status = status;
    change.lastError = error;
    change.lastAttempt = new Date().toISOString();
    if (status === 'error') {
      change.retryCount = (change.retryCount || 0) + 1;
    }
    await db.put('local_changes', change);
  }
};

export const clearSyncedChanges = async () => {
  const db = await getDB();
  const allChanges = await db.getAll('local_changes');
  const tx = db.transaction('local_changes', 'readwrite');
  for (const change of allChanges) {
    if (change.status === 'synced') {
      await tx.objectStore('local_changes').delete(change.id);
    }
  }
  await tx.done;
};

export const clearLocalChanges = async () => {
  const db = await getDB();
  const tx = db.transaction('local_changes', 'readwrite');
  await tx.objectStore('local_changes').clear();
};

// ============================================
// Sync metadata
// ============================================

export const getSyncMeta = async (key) => {
  const db = await getDB();
  return await db.get('sync_meta', key);
};

export const setSyncMeta = async (key, value) => {
  const db = await getDB();
  await db.put('sync_meta', { key, value, updatedAt: new Date().toISOString() });
};

export const getLastSyncTime = async (storeName = 'global') => {
  const meta = await getSyncMeta(`lastSync_${storeName}`);
  return meta?.value || null;
};

export const setLastSyncTime = async (storeName = 'global', time = null) => {
  await setSyncMeta(`lastSync_${storeName}`, time || new Date().toISOString());
};

// ============================================
// User data
// ============================================

export const saveUserData = async (user, token) => {
  const db = await getDB();
  await db.put('user', { key: 'currentUser', user, token, savedAt: new Date().toISOString() });
};

export const getUserData = async () => {
  const db = await getDB();
  return await db.get('user', 'currentUser');
};

export const clearUserData = async () => {
  const db = await getDB();
  await db.delete('user', 'currentUser');
};

// ============================================
// Utility functions
// ============================================

export const getUnsyncedItems = async (storeName) => {
  const db = await getDB();
  const items = await db.getAll(storeName);
  return items.filter(item => item._synced === false);
};

export const markItemAsSynced = async (storeName, id) => {
  const db = await getDB();
  const item = await db.get(storeName, id);
  if (item) {
    item._synced = true;
    item._lastSyncedAt = new Date().toISOString();
    await db.put(storeName, item);
  }
};

export const getStoreCounts = async () => {
  const db = await getDB();
  const counts = {};
  for (const store of SYNC_STORES) {
    try {
      const items = await db.getAll(store);
      counts[store] = {
        total: items.length,
        unsynced: items.filter(i => !i._synced).length,
        deleted: items.filter(i => i._deleted).length
      };
    } catch (e) {
      counts[store] = { total: 0, unsynced: 0, deleted: 0 };
    }
  }
  return counts;
};
