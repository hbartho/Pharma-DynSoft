/**
 * Hook pour gérer les données en mode offline
 * Fait un fallback automatique vers IndexedDB quand l'API est indisponible
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { getAllItems, bulkAddItems } from '../services/indexedDB';

/**
 * Hook générique pour récupérer des données avec fallback offline
 */
export const useOfflineQuery = (queryKey, apiEndpoint, storeName, options = {}) => {
  return useQuery({
    queryKey: queryKey,
    queryFn: async () => {
      // Vérifier si on est en ligne
      if (navigator.onLine) {
        try {
          const response = await api.get(apiEndpoint);
          const data = response.data;
          
          // Normaliser les données (certaines APIs retournent { items: [...] })
          const items = Array.isArray(data) ? data : (data.items || data);
          
          // Sauvegarder dans IndexedDB pour le mode offline
          if (Array.isArray(items) && items.length > 0 && storeName) {
            try {
              await bulkAddItems(storeName, items);
            } catch (cacheError) {
              console.warn(`Failed to cache ${storeName} data:`, cacheError);
            }
          }
          
          return data;
        } catch (apiError) {
          console.warn(`API error for ${apiEndpoint}, falling back to cache:`, apiError.message);
          // En cas d'erreur API, essayer IndexedDB
          return await getFromCache(storeName, apiEndpoint);
        }
      } else {
        // Hors ligne - utiliser IndexedDB
        console.log(`Offline mode: loading ${storeName} from cache`);
        return await getFromCache(storeName, apiEndpoint);
      }
    },
    staleTime: options.staleTime || 2 * 60 * 1000, // 2 minutes par défaut
    gcTime: options.gcTime || 30 * 60 * 1000, // 30 minutes
    retry: navigator.onLine ? 1 : 0, // Pas de retry si offline
    ...options,
  });
};

/**
 * Récupère les données depuis IndexedDB
 */
const getFromCache = async (storeName, apiEndpoint) => {
  if (!storeName) {
    throw new Error(`No cache available for ${apiEndpoint}`);
  }
  
  const cachedData = await getAllItems(storeName);
  
  if (!cachedData || cachedData.length === 0) {
    console.warn(`No cached data found for ${storeName}`);
    // Retourner un objet vide compatible avec le format attendu
    return { items: [], total: 0, page: 1, pages: 1 };
  }
  
  console.log(`Loaded ${cachedData.length} items from ${storeName} cache`);
  return cachedData;
};

/**
 * Hook pour les ventes avec support offline
 */
export const useOfflineSales = (params = {}, options = {}) => {
  const { limit = 100 } = params;
  
  return useOfflineQuery(
    ['sales', 'offline', params],
    `/sales?limit=${limit}`,
    'sales',
    {
      select: (data) => {
        // Normaliser la réponse
        if (Array.isArray(data)) {
          return { items: data, total: data.length, page: 1, pages: 1 };
        }
        return data;
      },
      ...options
    }
  );
};

/**
 * Hook pour les produits avec support offline
 */
export const useOfflineProducts = (options = {}) => {
  return useOfflineQuery(
    ['products', 'offline'],
    '/products',
    'products',
    options
  );
};

/**
 * Hook pour les clients avec support offline
 */
export const useOfflineCustomers = (options = {}) => {
  return useOfflineQuery(
    ['customers', 'offline'],
    '/customers',
    'customers',
    options
  );
};

/**
 * Hook pour les fournisseurs avec support offline
 */
export const useOfflineSuppliers = (options = {}) => {
  return useOfflineQuery(
    ['suppliers', 'offline'],
    '/suppliers',
    'suppliers',
    options
  );
};

/**
 * Hook pour les approvisionnements avec support offline
 */
export const useOfflineSupplies = (options = {}) => {
  return useOfflineQuery(
    ['supplies', 'offline'],
    '/supplies',
    'supplies',
    options
  );
};

/**
 * Hook pour les catégories avec support offline
 */
export const useOfflineCategories = (options = {}) => {
  return useOfflineQuery(
    ['categories', 'offline'],
    '/categories',
    'categories',
    options
  );
};

/**
 * Hook pour les unités avec support offline
 */
export const useOfflineUnits = (options = {}) => {
  return useOfflineQuery(
    ['units', 'offline'],
    '/units',
    'units',
    options
  );
};

export default {
  useOfflineQuery,
  useOfflineSales,
  useOfflineProducts,
  useOfflineCustomers,
  useOfflineSuppliers,
  useOfflineSupplies,
  useOfflineCategories,
  useOfflineUnits,
};
