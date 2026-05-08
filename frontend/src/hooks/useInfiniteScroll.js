/**
 * Generic Infinite Scroll Hook
 * Hook réutilisable pour implémenter le scroll infini sur toutes les pages
 * Avec support offline via IndexedDB
 */

import { useInfiniteQuery } from '@tanstack/react-query';
import api from '../services/api';
import { getAllItems, bulkAddItems } from '../services/indexedDB';

// Mapping des endpoints vers les stores IndexedDB
const ENDPOINT_TO_STORE = {
  '/customers/paginated': 'customers',
  '/suppliers/paginated': 'suppliers',
  '/supplies/paginated': 'supplies',
  '/prescriptions/paginated': 'prescriptions',
  '/products/paginated': 'products',
  '/sales': 'sales',
  '/stock/movements/paginated': 'stockMovements',
  '/stock/losses/paginated': 'stockLosses',
};

/**
 * Récupérer les données offline avec pagination simulée
 */
const getOfflinePageData = async (storeName, page, limit, filterParams) => {
  let allItems = await getAllItems(storeName) || [];
  
  // Appliquer les filtres de base
  if (filterParams.search) {
    const searchLower = filterParams.search.toLowerCase();
    allItems = allItems.filter(item => 
      (item.name || '').toLowerCase().includes(searchLower) ||
      (item.phone || '').toLowerCase().includes(searchLower) ||
      (item.email || '').toLowerCase().includes(searchLower) ||
      (item.code || '').toLowerCase().includes(searchLower)
    );
  }
  
  if (filterParams.status && filterParams.status !== 'all') {
    if (filterParams.status === 'active') {
      allItems = allItems.filter(item => item.is_active !== false);
    } else if (filterParams.status === 'inactive') {
      allItems = allItems.filter(item => item.is_active === false);
    } else {
      allItems = allItems.filter(item => item.status === filterParams.status);
    }
  }
  
  // Trier par nom ou date
  allItems.sort((a, b) => {
    if (a.name && b.name) return a.name.localeCompare(b.name);
    if (a.created_at && b.created_at) return new Date(b.created_at) - new Date(a.created_at);
    return 0;
  });
  
  // Pagination
  const start = (page - 1) * limit;
  const items = allItems.slice(start, start + limit);
  const total = allItems.length;
  const pages = Math.ceil(total / limit) || 1;
  
  return { items, total, page, pages, limit, _offline: true };
};

/**
 * Hook générique pour le scroll infini avec pagination serveur
 * Avec support offline automatique
 * @param {string} queryKey - Clé unique pour React Query
 * @param {string} endpoint - Endpoint API (ex: '/customers/paginated')
 * @param {Object} params - Paramètres de filtrage (search, status, etc.)
 * @param {Object} options - Options supplémentaires pour React Query
 */
export const useInfiniteList = (queryKey, endpoint, params = {}, options = {}) => {
  const { limit = 20, ...filterParams } = params;
  const storeName = ENDPOINT_TO_STORE[endpoint] || queryKey;

  return useInfiniteQuery({
    queryKey: [queryKey, 'infinite', { limit, ...filterParams }],
    queryFn: async ({ pageParam = 1 }) => {
      // Vérifier si online
      if (navigator.onLine) {
        try {
          const queryParams = new URLSearchParams();
          queryParams.append('page', pageParam.toString());
          queryParams.append('limit', limit.toString());
          
          // Ajouter tous les filtres non-vides
          Object.entries(filterParams).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '' && value !== 'all') {
              queryParams.append(key, value.toString());
            }
          });

          const response = await api.get(`${endpoint}?${queryParams.toString()}`);
          
          // Mettre en cache les données
          if (response.data.items && response.data.items.length > 0 && storeName) {
            try {
              await bulkAddItems(storeName, response.data.items);
            } catch (e) {
              console.warn(`Cache write failed for ${storeName}:`, e);
            }
          }
          
          return response.data;
        } catch (error) {
          console.warn(`API failed for ${endpoint}, using offline data:`, error.message);
          // Fallback vers IndexedDB
          return await getOfflinePageData(storeName, pageParam, limit, filterParams);
        }
      } else {
        // Mode offline - utiliser IndexedDB
        console.log(`Offline mode: loading ${storeName} from cache`);
        return await getOfflinePageData(storeName, pageParam, limit, filterParams);
      }
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.pages) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 30 * 1000, // 30 secondes
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

// ============================================
// Hooks spécifiques pour chaque module
// ============================================

/**
 * Hook pour les clients avec infinite scroll
 */
export const useCustomersInfinite = (params = {}, options = {}) => {
  return useInfiniteList('customers', '/customers/paginated', params, options);
};

/**
 * Hook pour les fournisseurs avec infinite scroll
 */
export const useSuppliersInfinite = (params = {}, options = {}) => {
  return useInfiniteList('suppliers', '/suppliers/paginated', params, options);
};

/**
 * Hook pour les approvisionnements avec infinite scroll
 */
export const useSuppliesInfinite = (params = {}, options = {}) => {
  return useInfiniteList('supplies', '/supplies/paginated', params, options);
};

/**
 * Hook pour les ordonnances avec infinite scroll
 */
export const usePrescriptionsInfinite = (params = {}, options = {}) => {
  return useInfiniteList('prescriptions', '/prescriptions/paginated', params, options);
};

/**
 * Hook pour les dettes avec infinite scroll
 */
export const useDebtsInfinite = (params = {}, options = {}) => {
  return useInfiniteList('debts', '/debts/paginated', params, options);
};

/**
 * Hook pour les mouvements de stock avec infinite scroll
 */
export const useStockMovementsInfinite = (params = {}, options = {}) => {
  // Convertir les noms de paramètres du frontend vers le backend
  const { productId, movementType, ...rest } = params;
  const backendParams = {
    ...rest,
    product_id: productId,
    movement_type: movementType,
  };
  return useInfiniteList('stockMovements', '/stock/movements/paginated', backendParams, options);
};

/**
 * Hook pour les pertes de stock avec infinite scroll
 */
export const useStockLossesInfinite = (params = {}, options = {}) => {
  return useInfiniteList('stockLosses', '/stock/losses/paginated', params, options);
};

/**
 * Hook pour l'historique des shifts avec infinite scroll
 */
export const useShiftsInfinite = (params = {}, options = {}) => {
  return useInfiniteList('shifts', '/shifts/paginated', params, options);
};

/**
 * Hook pour l'historique des prix avec infinite scroll
 */
export const usePriceHistoryInfinite = (params = {}, options = {}) => {
  return useInfiniteList('priceHistory', '/prices/history/paginated', params, options);
};

/**
 * Hook pour l'inventaire avec infinite scroll
 */
export const useInventoryMovementsInfinite = (params = {}, options = {}) => {
  return useInfiniteList('inventoryMovements', '/inventory/movements', params, options);
};

/**
 * Hook pour l'historique des opérations (ventes + retours) avec infinite scroll
 */
export const useOperationsHistoryInfinite = (params = {}, options = {}) => {
  return useInfiniteList('operationsHistory', '/returns/history/paginated', params, options);
};

export default {
  useInfiniteList,
  useCustomersInfinite,
  useSuppliersInfinite,
  useSuppliesInfinite,
  usePrescriptionsInfinite,
  useDebtsInfinite,
  useStockMovementsInfinite,
  useStockLossesInfinite,
  useShiftsInfinite,
  usePriceHistoryInfinite,
  useInventoryMovementsInfinite,
  useOperationsHistoryInfinite,
};
