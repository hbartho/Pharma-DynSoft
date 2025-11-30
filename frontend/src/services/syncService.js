import api from './api';
import {
  getLocalChanges,
  clearLocalChanges,
  addItem,
  getAllItems,
} from './indexedDB';

export const syncData = async () => {
  try {
    // Check if online
    if (!navigator.onLine) {
      return { success: false, message: 'Offline' };
    }

    // Push local changes to server
    const localChanges = await getLocalChanges();
    if (localChanges.length > 0) {
      await api.post('/sync/push', { changes: localChanges });
      await clearLocalChanges();
    }

    // Pull latest data from server
    const response = await api.get('/sync/pull');
    const { products, sales, customers } = response.data;

    // Update IndexedDB with server data
    for (const product of products) {
      await addItem('products', product);
    }

    for (const sale of sales) {
      await addItem('sales', sale);
    }

    for (const customer of customers) {
      await addItem('customers', customer);
    }

    return { success: true, message: 'Sync completed' };
  } catch (error) {
    console.error('Sync error:', error);
    return { success: false, message: error.message };
  }
};

export const autoSync = () => {
  // Sync every 5 minutes if online
  setInterval(async () => {
    if (navigator.onLine) {
      await syncData();
    }
  }, 5 * 60 * 1000);
};