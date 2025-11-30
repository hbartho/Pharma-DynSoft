import { openDB } from 'idb';

const DB_NAME = 'PharmaFlowDB';
const DB_VERSION = 1;

let dbInstance = null;

export const initDB = async () => {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB(DB_NAME, DB_VERSION, {
    upgrade(db) {
      if (!db.objectStoreNames.contains('products')) {
        db.createObjectStore('products', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('sales')) {
        db.createObjectStore('sales', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('customers')) {
        db.createObjectStore('customers', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('suppliers')) {
        db.createObjectStore('suppliers', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('prescriptions')) {
        db.createObjectStore('prescriptions', { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains('local_changes')) {
        db.createObjectStore('local_changes', { keyPath: 'id', autoIncrement: true });
      }
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

// Generic CRUD operations
export const addItem = async (storeName, item) => {
  const db = await getDB();
  await db.put(storeName, item);
  return item;
};

export const getItem = async (storeName, id) => {
  const db = await getDB();
  return await db.get(storeName, id);
};

export const getAllItems = async (storeName) => {
  const db = await getDB();
  return await db.getAll(storeName);
};

export const updateItem = async (storeName, item) => {
  const db = await getDB();
  await db.put(storeName, item);
  return item;
};

export const deleteItem = async (storeName, id) => {
  const db = await getDB();
  await db.delete(storeName, id);
};

// Local changes tracking
export const addLocalChange = async (type, action, payload) => {
  const db = await getDB();
  const change = {
    type,
    action,
    payload,
    timestamp: new Date().toISOString(),
  };
  await db.add('local_changes', change);
  return change;
};

export const getLocalChanges = async () => {
  const db = await getDB();
  return await db.getAll('local_changes');
};

export const clearLocalChanges = async () => {
  const db = await getDB();
  const tx = db.transaction('local_changes', 'readwrite');
  await tx.objectStore('local_changes').clear();
};

// User data
export const saveUserData = async (user, token) => {
  const db = await getDB();
  await db.put('user', { key: 'currentUser', user, token });
};

export const getUserData = async () => {
  const db = await getDB();
  return await db.get('user', 'currentUser');
};

export const clearUserData = async () => {
  const db = await getDB();
  await db.delete('user', 'currentUser');
};