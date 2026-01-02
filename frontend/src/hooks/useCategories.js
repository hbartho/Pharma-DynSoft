/**
 * React Query Hooks - Catégories
 * Hooks pour la gestion des catégories avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer toutes les catégories
 */
export const useCategories = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: async () => {
      const response = await api.get('/categories');
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes (les catégories changent rarement)
    ...options,
  });
};

/**
 * Récupérer une catégorie par ID
 */
export const useCategory = (categoryId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.category(categoryId),
    queryFn: async () => {
      const response = await api.get(`/categories/${categoryId}`);
      return response.data;
    },
    enabled: !!categoryId,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer une catégorie
 */
export const useCreateCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (categoryData) => {
      const response = await api.post('/categories', categoryData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
      toast.success('Catégorie créée avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création de la catégorie', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour une catégorie
 */
export const useUpdateCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ categoryId, data }) => {
      const response = await api.put(`/categories/${categoryId}`, data);
      return response.data;
    },
    onSuccess: (updatedCategory) => {
      queryClient.setQueryData(queryKeys.category(updatedCategory.id), updatedCategory);
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
      // Invalider aussi les produits car le markup peut avoir changé
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      toast.success('Catégorie mise à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour de la catégorie', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer une catégorie
 */
export const useDeleteCategory = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (categoryId) => {
      await api.delete(`/categories/${categoryId}`);
      return categoryId;
    },
    onSuccess: (categoryId) => {
      queryClient.removeQueries({ queryKey: queryKeys.category(categoryId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.categories });
      toast.success('Catégorie supprimée avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression de la catégorie', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Obtenir une catégorie par ID depuis le cache
 */
export const useCategoryById = (categoryId) => {
  const { data: categories = [] } = useCategories();
  return categories.find((cat) => cat.id === categoryId) || null;
};

/**
 * Obtenir le nom d'une catégorie
 */
export const useCategoryName = (categoryId) => {
  const category = useCategoryById(categoryId);
  return category?.name || 'Sans catégorie';
};

/**
 * Options pour les selects de catégories
 */
export const useCategoryOptions = () => {
  const { data: categories = [], isLoading } = useCategories();
  
  const options = categories.map((cat) => ({
    value: cat.id,
    label: cat.name,
    markup: cat.markup_coefficient,
  }));

  return { options, isLoading };
};

export default {
  useCategories,
  useCategory,
  useCreateCategory,
  useUpdateCategory,
  useDeleteCategory,
  useCategoryById,
  useCategoryName,
  useCategoryOptions,
};
