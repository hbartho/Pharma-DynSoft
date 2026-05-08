/**
 * React Query Hooks - Unités
 * Hooks pour la gestion des unités avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer toutes les unités
 */
export const useUnits = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.units,
    queryFn: async () => {
      const response = await api.get('/units');
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer une unité
 */
export const useCreateUnit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (unitData) => {
      const response = await api.post('/units', unitData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.units });
      toast.success('Unité créée avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création de l\'unité', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour une unité
 */
export const useUpdateUnit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ unitId, data }) => {
      const response = await api.put(`/units/${unitId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.units });
      toast.success('Unité mise à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour de l\'unité', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer une unité
 */
export const useDeleteUnit = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (unitId) => {
      await api.delete(`/units/${unitId}`);
      return unitId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.units });
      toast.success('Unité supprimée avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression de l\'unité', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Options pour les selects d'unités
 */
export const useUnitOptions = () => {
  const { data: units = [], isLoading } = useUnits();
  
  const options = units.map((unit) => ({
    value: unit.id,
    label: unit.name,
    abbreviation: unit.abbreviation,
  }));

  return { options, isLoading };
};

/**
 * Obtenir le nom d'une unité par ID
 */
export const useUnitName = (unitId) => {
  const { data: units = [] } = useUnits();
  const unit = units.find((u) => u.id === unitId);
  return unit?.name || '';
};

export default {
  useUnits,
  useCreateUnit,
  useUpdateUnit,
  useDeleteUnit,
  useUnitOptions,
  useUnitName,
};
