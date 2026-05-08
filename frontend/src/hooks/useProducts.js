/**
 * React Query Hooks - Produits
 * Hooks pour la gestion des produits avec cache intelligent et support offline
 */

import { useQuery, useInfiniteQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';
import { getAllItems, bulkAddItems } from '../services/indexedDB';

// ============================================
// Helper pour le fallback offline
// ============================================

const fetchProductsWithOffline = async (apiCall, transformFn = null) => {
  if (navigator.onLine) {
    try {
      const response = await apiCall();
      const data = response.data;
      
      // Mettre en cache
      const items = Array.isArray(data) ? data : (data.items || []);
      if (items.length > 0) {
        try {
          await bulkAddItems('products', items);
        } catch (e) {
          console.warn('Products cache write failed:', e);
        }
      }
      
      return transformFn ? transformFn(data) : data;
    } catch (error) {
      console.warn('Products API failed, using cache:', error.message);
      const cached = await getAllItems('products');
      return transformFn ? transformFn(cached) : cached;
    }
  } else {
    console.log('Offline: loading products from cache');
    const cached = await getAllItems('products');
    return transformFn ? transformFn(cached) : cached;
  }
};

// ============================================
// Queries
// ============================================

/**
 * Récupérer les produits avec infinite scroll
 * Avec support offline
 */
export const useProductsInfinite = (params = {}, options = {}) => {
  const {
    limit = 20,
    search = '',
    categoryId = '',
    status = ''
  } = params;

  return useInfiniteQuery({
    queryKey: ['products', 'infinite', { limit, search, categoryId, status }],
    queryFn: async ({ pageParam = 1 }) => {
      if (navigator.onLine) {
        try {
          const queryParams = new URLSearchParams();
          queryParams.append('page', pageParam.toString());
          queryParams.append('limit', limit.toString());
          
          if (search) queryParams.append('search', search);
          if (categoryId && categoryId !== 'all') queryParams.append('category_id', categoryId);
          if (status && status !== 'all') queryParams.append('status', status);

          const response = await api.get(`/products/paginated?${queryParams.toString()}`);
          
          // Cache
          if (response.data.items?.length > 0) {
            try {
              await bulkAddItems('products', response.data.items);
            } catch (e) {}
          }
          
          return response.data;
        } catch (error) {
          return await getOfflineProductsPage(pageParam, limit, { search, categoryId, status });
        }
      } else {
        return await getOfflineProductsPage(pageParam, limit, { search, categoryId, status });
      }
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.pages) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 30 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

// Helper pour la pagination offline des produits
const getOfflineProductsPage = async (page, limit, filters) => {
  let allProducts = await getAllItems('products');
  
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    allProducts = allProducts.filter(p => 
      p.name?.toLowerCase().includes(searchLower) ||
      p.barcode?.toLowerCase().includes(searchLower)
    );
  }
  if (filters.categoryId && filters.categoryId !== 'all') {
    allProducts = allProducts.filter(p => p.category_id === filters.categoryId);
  }
  
  allProducts.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
  
  const start = (page - 1) * limit;
  const items = allProducts.slice(start, start + limit);
  const total = allProducts.length;
  const pages = Math.ceil(total / limit);
  
  return { items, total, page, pages, limit };
};

/**
 * Récupérer tous les produits
 * Avec support offline
 */
export const useProducts = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.products,
    queryFn: async () => {
      return await fetchProductsWithOffline(() => api.get('/products'));
    },
    staleTime: 5 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
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

/**
 * Activer/Désactiver un produit
 */
export const useToggleProductStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (productId) => {
      const response = await api.patch(`/products/${productId}/toggle-status`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      toast.success(data.message || 'Statut du produit modifié');
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
  useProductsInfinite,
  useProduct,
  useProductAlerts,
  useCreateProduct,
  useUpdateProduct,
  useDeleteProduct,
  useToggleProductStatus,
  useProductSearch,
  useLowStockProducts,
};
