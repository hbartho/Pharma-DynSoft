/**
 * React Query Hooks - Approvisionnements
 * Hooks pour la gestion des approvisionnements avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les approvisionnements
 */
export const useSupplies = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.supplies,
    queryFn: async () => {
      const response = await api.get('/supplies');
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
};

/**
 * Récupérer un approvisionnement par ID
 */
export const useSupply = (supplyId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.supply(supplyId),
    queryFn: async () => {
      const response = await api.get(`/supplies/${supplyId}`);
      return response.data;
    },
    enabled: !!supplyId,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un approvisionnement
 */
export const useCreateSupply = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplyData) => {
      const response = await api.post('/supplies', supplyData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.supplies });
      toast.success('Approvisionnement créé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création de l\'approvisionnement', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour un approvisionnement
 */
export const useUpdateSupply = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ supplyId, data }) => {
      const response = await api.put(`/supplies/${supplyId}`, data);
      return response.data;
    },
    onSuccess: (updatedSupply) => {
      queryClient.setQueryData(queryKeys.supply(updatedSupply.id), updatedSupply);
      queryClient.invalidateQueries({ queryKey: queryKeys.supplies });
      toast.success('Approvisionnement mis à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer un approvisionnement
 */
export const useDeleteSupply = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplyId) => {
      await api.delete(`/supplies/${supplyId}`);
      return supplyId;
    },
    onSuccess: (supplyId) => {
      queryClient.removeQueries({ queryKey: queryKeys.supply(supplyId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.supplies });
      toast.success('Approvisionnement supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Valider un approvisionnement (crée les lots de stock)
 */
export const useValidateSupply = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplyId) => {
      const response = await api.post(`/supplies/${supplyId}/validate`);
      return response.data;
    },
    onSuccess: (validatedSupply) => {
      // Invalider toutes les données liées au stock
      queryClient.invalidateQueries({ queryKey: queryKeys.supplies });
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      queryClient.invalidateQueries({ queryKey: queryKeys.stockMovements });
      toast.success('Approvisionnement validé - Stock mis à jour');
    },
    onError: (error) => {
      toast.error('Erreur lors de la validation', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Filtrer par statut
 */
export const useSuppliesByStatus = (status) => {
  const { data: supplies = [], ...rest } = useSupplies();
  const filteredSupplies = status 
    ? supplies.filter(s => s.status === status)
    : supplies;
  return { data: filteredSupplies, ...rest };
};

/**
 * Approvisionnements en attente
 */
export const usePendingSupplies = () => {
  return useSuppliesByStatus('pending');
};

/**
 * Approvisionnements validés
 */
export const useValidatedSupplies = () => {
  return useSuppliesByStatus('validated');
};

/**
 * Rechercher des approvisionnements
 */
export const useSupplySearch = (searchTerm = '', supplierId = null) => {
  const { data: supplies = [], ...rest } = useSupplies();

  const filteredSupplies = supplies.filter((supply) => {
    const matchesSearch = !searchTerm || 
      supply.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      supply.supplier_name?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesSupplier = !supplierId || supply.supplier_id === supplierId;

    return matchesSearch && matchesSupplier;
  });

  return { data: filteredSupplies, ...rest };
};

export default {
  useSupplies,
  useSupply,
  useCreateSupply,
  useUpdateSupply,
  useDeleteSupply,
  useValidateSupply,
  useSuppliesByStatus,
  usePendingSupplies,
  useValidatedSupplies,
  useSupplySearch,
};
