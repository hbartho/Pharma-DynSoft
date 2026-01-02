/**
 * React Query Hooks - Produits
 * Hooks pour la gestion des produits avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les produits
 */
export const useProducts = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.products,
    queryFn: async () => {
      const response = await api.get('/products');
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
};

/**
 * Récupérer un produit par ID
 */
export const useProduct = (productId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.product(productId),
    queryFn: async () => {
      const response = await api.get(`/products/${productId}`);
      return response.data;
    },
    enabled: !!productId,
    ...options,
  });
};

/**
 * Récupérer les alertes produits (stock bas, péremption)
 */
export const useProductAlerts = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.productAlerts,
    queryFn: async () => {
      const response = await api.get('/products/alerts');
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un produit
 */
export const useCreateProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (productData) => {
      const response = await api.post('/products', productData);
      return response.data;
    },
    onSuccess: (newProduct) => {
      // Invalider la liste des produits
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      toast.success('Produit créé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création du produit', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour un produit
 */
export const useUpdateProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ productId, data }) => {
      const response = await api.put(`/products/${productId}`, data);
      return response.data;
    },
    onSuccess: (updatedProduct) => {
      // Mettre à jour le cache
      queryClient.setQueryData(queryKeys.product(updatedProduct.id), updatedProduct);
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      toast.success('Produit mis à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour du produit', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer un produit
 */
export const useDeleteProduct = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (productId) => {
      await api.delete(`/products/${productId}`);
      return productId;
    },
    onSuccess: (productId) => {
      // Supprimer du cache
      queryClient.removeQueries({ queryKey: queryKeys.product(productId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      toast.success('Produit supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression du produit', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Rechercher des produits (côté client)
 */
export const useProductSearch = (searchTerm = '', categoryId = null) => {
  const { data: products = [], ...rest } = useProducts();

  const filteredProducts = products.filter((product) => {
    const matchesSearch = !searchTerm || 
      product.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.internal_reference?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = !categoryId || categoryId === 'all' || 
      product.category_id === categoryId;

    return matchesSearch && matchesCategory;
  });

  return { data: filteredProducts, ...rest };
};

/**
 * Produits avec stock bas
 */
export const useLowStockProducts = (threshold = 10) => {
  const { data: products = [], ...rest } = useProducts();

  const lowStockProducts = products.filter(
    (product) => product.quantity_in_stock <= threshold
  );

  return { data: lowStockProducts, ...rest };
};

export default {
  useProducts,
  useProduct,
  useProductAlerts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useProductSearch,
  useLowStockProducts,
};
