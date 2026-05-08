/**
 * React Query Hooks - Fournisseurs
 * Hooks pour la gestion des fournisseurs avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les fournisseurs
 */
export const useSuppliers = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.suppliers,
    queryFn: async () => {
      const response = await api.get('/suppliers');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    ...options,
  });
};

/**
 * Récupérer uniquement les fournisseurs actifs
 */
export const useActiveSuppliers = (options = {}) => {
  const { data: suppliers = [], ...rest } = useSuppliers(options);
  const activeSuppliers = suppliers.filter(s => s.is_active !== false);
  return { data: activeSuppliers, ...rest };
};

/**
 * Récupérer un fournisseur par ID
 */
export const useSupplier = (supplierId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.supplier(supplierId),
    queryFn: async () => {
      const response = await api.get(`/suppliers/${supplierId}`);
      return response.data;
    },
    enabled: !!supplierId,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un fournisseur
 */
export const useCreateSupplier = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplierData) => {
      const response = await api.post('/suppliers', supplierData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.suppliers });
      toast.success('Fournisseur créé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création du fournisseur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour un fournisseur
 */
export const useUpdateSupplier = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ supplierId, data }) => {
      const response = await api.put(`/suppliers/${supplierId}`, data);
      return response.data;
    },
    onSuccess: (updatedSupplier) => {
      queryClient.setQueryData(queryKeys.supplier(updatedSupplier.id), updatedSupplier);
      queryClient.invalidateQueries({ queryKey: queryKeys.suppliers });
      toast.success('Fournisseur mis à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour du fournisseur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer un fournisseur
 */
export const useDeleteSupplier = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplierId) => {
      await api.delete(`/suppliers/${supplierId}`);
      return supplierId;
    },
    onSuccess: (supplierId) => {
      queryClient.removeQueries({ queryKey: queryKeys.supplier(supplierId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.suppliers });
      toast.success('Fournisseur supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression du fournisseur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Activer/Désactiver un fournisseur
 */
export const useToggleSupplierStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (supplierId) => {
      const response = await api.patch(`/suppliers/${supplierId}/toggle-status`);
      return response.data;
    },
    onSuccess: (updatedSupplier) => {
      queryClient.setQueryData(queryKeys.supplier(updatedSupplier.id), updatedSupplier);
      queryClient.invalidateQueries({ queryKey: queryKeys.suppliers });
      toast.success(
        updatedSupplier.is_active 
          ? 'Fournisseur activé' 
          : 'Fournisseur désactivé'
      );
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
 * Rechercher des fournisseurs
 */
export const useSupplierSearch = (searchTerm = '') => {
  const { data: suppliers = [], ...rest } = useSuppliers();

  const filteredSuppliers = suppliers.filter((supplier) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      supplier.name?.toLowerCase().includes(term) ||
      supplier.contact?.toLowerCase().includes(term) ||
      supplier.phone?.includes(term)
    );
  });

  return { data: filteredSuppliers, ...rest };
};

/**
 * Options pour les selects de fournisseurs (actifs uniquement)
 */
export const useSupplierOptions = () => {
  const { data: suppliers = [], isLoading } = useActiveSuppliers();
  
  const options = suppliers.map((supplier) => ({
    value: supplier.id,
    label: supplier.name,
  }));

  return { options, isLoading };
};

export default {
  useSuppliers,
  useActiveSuppliers,
  useSupplier,
  useCreateSupplier,
  useUpdateSupplier,
  useDeleteSupplier,
  useToggleSupplierStatus,
  useSupplierSearch,
  useSupplierOptions,
};
