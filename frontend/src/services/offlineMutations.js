/**
 * React Query Offline Mutation Hook
 * Permet de créer des mutations qui fonctionnent en mode offline
 * et se synchronisent automatiquement au retour en ligne
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { addLocalChange, addItemLocal, updateItem, getItem, softDeleteItem } from './indexedDB';
import { syncOperation } from './offlineService';
import api from './api';
import { toast } from 'sonner';
import { v4 as uuidv4 } from 'uuid';

/**
 * Types d'entités supportées pour les opérations offline
 */
export const OFFLINE_ENTITIES = {
  products: {
    endpoint: '/products',
    queryKey: ['products'],
    storeName: 'products',
    label: 'Produit',
  },
  categories: {
    endpoint: '/categories',
    queryKey: ['categories'],
    storeName: 'categories',
    label: 'Catégorie',
  },
  customers: {
    endpoint: '/customers',
    queryKey: ['customers'],
    storeName: 'customers',
    label: 'Client',
  },
  suppliers: {
    endpoint: '/suppliers',
    queryKey: ['suppliers'],
    storeName: 'suppliers',
    label: 'Fournisseur',
  },
  sales: {
    endpoint: '/sales',
    queryKey: ['sales'],
    storeName: 'sales',
    label: 'Vente',
  },
  returns: {
    endpoint: '/returns',
    queryKey: ['returns'],
    storeName: 'returns',
    label: 'Retour',
  },
  supplies: {
    endpoint: '/supplies',
    queryKey: ['supplies'],
    storeName: 'supplies',
    label: 'Approvisionnement',
  },
  prescriptions: {
    endpoint: '/prescriptions',
    queryKey: ['prescriptions'],
    storeName: 'prescriptions',
    label: 'Ordonnance',
  },
  units: {
    endpoint: '/units',
    queryKey: ['units'],
    storeName: 'units',
    label: 'Unité',
  },
};

/**
 * Hook pour créer une mutation offline-first
 * @param {string} entityType - Type d'entité (products, customers, etc.)
 * @param {string} action - Action (create, update, delete)
 * @param {object} options - Options supplémentaires
 */
export const useOfflineMutation = (entityType, action = 'create', options = {}) => {
  const queryClient = useQueryClient();
  const entity = OFFLINE_ENTITIES[entityType];

  if (!entity) {
    throw new Error(`Entity type not supported: ${entityType}`);
  }

  const {
    onSuccess: customOnSuccess,
    onError: customOnError,
    showToast = true,
    invalidateQueries = true,
    optimisticUpdate = true,
  } = options;

  return useMutation({
    mutationFn: async (data) => {
      const isOnline = navigator.onLine;

      if (isOnline) {
        // Mode en ligne - essayer l'API d'abord
        try {
          let response;
          switch (action) {
            case 'create':
              response = await api.post(entity.endpoint, data);
              return { ...response.data, _synced: true, _offline: false };
            case 'update':
              response = await api.put(`${entity.endpoint}/${data.id}`, data);
              return { ...response.data, _synced: true, _offline: false };
            case 'delete':
              await api.delete(`${entity.endpoint}/${data.id || data}`);
              return { id: data.id || data, _deleted: true };
            default:
              throw new Error(`Unknown action: ${action}`);
          }
        } catch (error) {
          // Si erreur réseau, basculer en mode offline
          if (error.code === 'ERR_NETWORK' || !navigator.onLine) {
            console.log('Network error, falling back to offline mode');
            return await handleOfflineOperation(entityType, action, data, entity);
          }
          throw error;
        }
      } else {
        // Mode hors ligne
        return await handleOfflineOperation(entityType, action, data, entity);
      }
    },

    onMutate: async (newData) => {
      if (!optimisticUpdate) return;

      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: entity.queryKey });

      // Snapshot the previous value
      const previousData = queryClient.getQueryData(entity.queryKey);

      // Optimistically update
      if (action === 'create') {
        const optimisticItem = {
          ...newData,
          id: newData.id || `temp-${uuidv4()}`,
          _pending: true,
        };
        queryClient.setQueryData(entity.queryKey, (old = []) => [...old, optimisticItem]);
      } else if (action === 'update') {
        queryClient.setQueryData(entity.queryKey, (old = []) =>
          old.map((item) => (item.id === newData.id ? { ...item, ...newData, _pending: true } : item))
        );
      } else if (action === 'delete') {
        const idToDelete = newData.id || newData;
        queryClient.setQueryData(entity.queryKey, (old = []) =>
          old.filter((item) => item.id !== idToDelete)
        );
      }

      return { previousData };
    },

    onError: (error, newData, context) => {
      // Rollback on error
      if (context?.previousData && optimisticUpdate) {
        queryClient.setQueryData(entity.queryKey, context.previousData);
      }

      if (showToast) {
        toast.error(`Erreur: ${entity.label}`, {
          description: error.response?.data?.detail || error.message,
        });
      }

      if (customOnError) {
        customOnError(error, newData, context);
      }
    },

    onSuccess: (data, variables, context) => {
      // Invalidate and refetch
      if (invalidateQueries) {
        queryClient.invalidateQueries({ queryKey: entity.queryKey });
      }

      const actionLabels = {
        create: 'créé',
        update: 'mis à jour',
        delete: 'supprimé',
      };

      if (showToast) {
        if (data._offline) {
          toast.warning(`${entity.label} ${actionLabels[action]} (hors-ligne)`, {
            description: 'Sera synchronisé au retour en ligne',
          });
        } else {
          toast.success(`${entity.label} ${actionLabels[action]} avec succès`);
        }
      }

      if (customOnSuccess) {
        customOnSuccess(data, variables, context);
      }
    },

    onSettled: () => {
      // Always refetch after mutation settles
      if (invalidateQueries) {
        queryClient.invalidateQueries({ queryKey: entity.queryKey });
      }
    },
  });
};

/**
 * Gère une opération en mode offline
 */
async function handleOfflineOperation(entityType, action, data, entity) {
  const offlineId = `offline-${entityType}-${uuidv4()}`;

  switch (action) {
    case 'create': {
      const offlineItem = {
        ...data,
        id: offlineId,
        _offline: true,
        _synced: false,
        _pendingSync: true,
        created_at: new Date().toISOString(),
      };

      // Sauvegarder dans IndexedDB
      await addItemLocal(entity.storeName, offlineItem);

      // Ajouter à la queue de synchronisation
      await addLocalChange(entityType, 'create', {
        ...data,
        _offlineId: offlineId,
      });

      return offlineItem;
    }

    case 'update': {
      const existingItem = await getItem(entity.storeName, data.id);
      const updatedItem = {
        ...existingItem,
        ...data,
        _offline: true,
        _synced: false,
        _pendingSync: true,
        updated_at: new Date().toISOString(),
      };

      await updateItem(entity.storeName, updatedItem);
      await addLocalChange(entityType, 'update', data);

      return updatedItem;
    }

    case 'delete': {
      const idToDelete = data.id || data;
      await softDeleteItem(entity.storeName, idToDelete);
      await addLocalChange(entityType, 'delete', { id: idToDelete });

      return { id: idToDelete, _deleted: true, _offline: true };
    }

    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

/**
 * Hook pour créer un produit (offline-first)
 */
export const useOfflineCreateProduct = (options = {}) => {
  return useOfflineMutation('products', 'create', options);
};

/**
 * Hook pour mettre à jour un produit (offline-first)
 */
export const useOfflineUpdateProduct = (options = {}) => {
  return useOfflineMutation('products', 'update', options);
};

/**
 * Hook pour supprimer un produit (offline-first)
 */
export const useOfflineDeleteProduct = (options = {}) => {
  return useOfflineMutation('products', 'delete', options);
};

/**
 * Hook pour créer un client (offline-first)
 */
export const useOfflineCreateCustomer = (options = {}) => {
  return useOfflineMutation('customers', 'create', options);
};

/**
 * Hook pour mettre à jour un client (offline-first)
 */
export const useOfflineUpdateCustomer = (options = {}) => {
  return useOfflineMutation('customers', 'update', options);
};

/**
 * Hook pour supprimer un client (offline-first)
 */
export const useOfflineDeleteCustomer = (options = {}) => {
  return useOfflineMutation('customers', 'delete', options);
};

/**
 * Hook pour créer un fournisseur (offline-first)
 */
export const useOfflineCreateSupplier = (options = {}) => {
  return useOfflineMutation('suppliers', 'create', options);
};

/**
 * Hook pour créer une vente (offline-first)
 */
export const useOfflineCreateSale = (options = {}) => {
  return useOfflineMutation('sales', 'create', {
    ...options,
    // Pour les ventes, on veut aussi invalider les produits (stock)
    onSuccess: (data, variables, context) => {
      if (options.onSuccess) {
        options.onSuccess(data, variables, context);
      }
    },
  });
};

export default {
  useOfflineMutation,
  useOfflineCreateProduct,
  useOfflineUpdateProduct,
  useOfflineDeleteProduct,
  useOfflineCreateCustomer,
  useOfflineUpdateCustomer,
  useOfflineDeleteCustomer,
  useOfflineCreateSupplier,
  useOfflineCreateSale,
  OFFLINE_ENTITIES,
};
