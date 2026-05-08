/**
 * React Query Hooks - Clients
 * Hooks pour la gestion des clients avec cache intelligent et support offline
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';
import { getAllItems, bulkAddItems, getItem } from '../services/indexedDB';

// ============================================
// Helper pour le fallback offline
// ============================================

const fetchCustomersWithOffline = async () => {
  if (navigator.onLine) {
    try {
      const response = await api.get('/customers');
      const data = response.data;
      
      // Mettre en cache
      if (Array.isArray(data) && data.length > 0) {
        try {
          await bulkAddItems('customers', data);
        } catch (e) {
          console.warn('Customers cache write failed:', e);
        }
      }
      
      return data;
    } catch (error) {
      console.warn('Customers API failed, using cache:', error.message);
      return await getAllItems('customers');
    }
  } else {
    console.log('Offline: loading customers from cache');
    return await getAllItems('customers');
  }
};

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les clients
 * Avec support offline
 */
export const useCustomers = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.customers,
    queryFn: fetchCustomersWithOffline,
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer un client par ID
 * Avec support offline
 */
export const useCustomer = (customerId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.customer(customerId),
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get(`/customers/${customerId}`);
          return response.data;
        } catch (error) {
          console.warn('Customer API failed, using cache:', error.message);
          return await getItem('customers', customerId);
        }
      } else {
        return await getItem('customers', customerId);
      }
    },
    enabled: !!customerId,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un client
 */
export const useCreateCustomer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (customerData) => {
      const response = await api.post('/customers', customerData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customers });
      toast.success('Client créé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création du client', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour un client
 */
export const useUpdateCustomer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ customerId, data }) => {
      const response = await api.put(`/customers/${customerId}`, data);
      return response.data;
    },
    onSuccess: (updatedCustomer) => {
      queryClient.setQueryData(queryKeys.customer(updatedCustomer.id), updatedCustomer);
      queryClient.invalidateQueries({ queryKey: queryKeys.customers });
      toast.success('Client mis à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour du client', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer un client
 */
export const useDeleteCustomer = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (customerId) => {
      await api.delete(`/customers/${customerId}`);
      return customerId;
    },
    onSuccess: (customerId) => {
      queryClient.removeQueries({ queryKey: queryKeys.customer(customerId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.customers });
      toast.success('Client supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression du client', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Activer/Désactiver un client
 */
export const useToggleCustomerStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (customerId) => {
      const response = await api.patch(`/customers/${customerId}/toggle-status`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customers });
      toast.success(data.message);
    },
    onError: (error) => {
      toast.error('Erreur lors du changement de statut', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Rechercher des clients
 */
export const useCustomerSearch = (searchTerm = '') => {
  const { data: customers = [], ...rest } = useCustomers();

  const filteredCustomers = customers.filter((customer) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      customer.name?.toLowerCase().includes(term) ||
      customer.phone?.includes(term) ||
      customer.email?.toLowerCase().includes(term)
    );
  });

  return { data: filteredCustomers, ...rest };
};

/**
 * Options pour les selects de clients (exclut les inactifs par défaut)
 */
export const useCustomerOptions = (includeInactive = false) => {
  const { data: customers = [], isLoading } = useCustomers();
  
  const options = customers
    .filter((customer) => includeInactive || customer.is_active !== false)
    .map((customer) => ({
      value: customer.id,
      label: customer.name,
      phone: customer.phone,
    }));

  return { options, isLoading };
};

export default {
  useCustomers,
  useCustomer,
  useCreateCustomer,
  useUpdateCustomer,
  useDeleteCustomer,
  useToggleCustomerStatus,
  useCustomerSearch,
  useCustomerOptions,
};
