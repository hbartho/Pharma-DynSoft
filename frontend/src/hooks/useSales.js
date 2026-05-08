/**
 * React Query Hooks - Ventes
 * Hooks pour la gestion des ventes avec cache intelligent et support offline
 */

import { useQuery, useInfiniteQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';
import { getAllItems, bulkAddItems } from '../services/indexedDB';

// ============================================
// Helper pour le fallback offline
// ============================================

const fetchWithOfflineFallback = async (apiCall, storeName, transformFn = null) => {
  if (navigator.onLine) {
    try {
      const response = await apiCall();
      const data = response.data;
      
      // Mettre en cache les données
      const items = Array.isArray(data) ? data : (data.items || []);
      if (items.length > 0 && storeName) {
        try {
          await bulkAddItems(storeName, items);
        } catch (e) {
          console.warn('Cache write failed:', e);
        }
      }
      
      return transformFn ? transformFn(data) : data;
    } catch (error) {
      console.warn('API failed, trying cache:', error.message);
      // Fallback vers le cache
      const cached = await getAllItems(storeName);
      if (cached && cached.length > 0) {
        return transformFn 
          ? transformFn({ items: cached, total: cached.length, page: 1, pages: 1 })
          : { items: cached, total: cached.length, page: 1, pages: 1 };
      }
      throw error;
    }
  } else {
    // Mode offline - utiliser le cache
    console.log('Offline mode: loading from cache');
    const cached = await getAllItems(storeName);
    const result = { items: cached || [], total: cached?.length || 0, page: 1, pages: 1 };
    return transformFn ? transformFn(result) : result;
  }
};

// ============================================
// Queries
// ============================================

/**
 * Récupérer les ventes avec infinite scroll
 * Avec support offline (fallback vers toutes les données en cache)
 */
export const useSalesInfinite = (params = {}, options = {}) => {
  const {
    limit = 20,
    search = '',
    dateFrom = '',
    dateTo = '',
    paymentMethod = '',
    agentCode = '',
    customerId = '',
    status = ''
  } = params;

  return useInfiniteQuery({
    queryKey: ['sales', 'infinite', { limit, search, dateFrom, dateTo, paymentMethod, agentCode, customerId, status }],
    queryFn: async ({ pageParam = 1 }) => {
      if (navigator.onLine) {
        try {
          const queryParams = new URLSearchParams();
          queryParams.append('page', pageParam.toString());
          queryParams.append('limit', limit.toString());
          
          if (search) queryParams.append('search', search);
          if (dateFrom) queryParams.append('date_from', dateFrom);
          if (dateTo) queryParams.append('date_to', dateTo);
          if (paymentMethod) queryParams.append('payment_method', paymentMethod);
          if (agentCode) queryParams.append('agent_code', agentCode);
          if (customerId) queryParams.append('customer_id', customerId);
          if (status) queryParams.append('status', status);

          const response = await api.get(`/sales?${queryParams.toString()}`);
          
          // Mettre en cache les nouvelles données
          if (response.data.items && response.data.items.length > 0) {
            try {
              await bulkAddItems('sales', response.data.items);
            } catch (e) {
              console.warn('Cache write failed:', e);
            }
          }
          
          return response.data;
        } catch (error) {
          console.warn('API failed, using cache:', error.message);
          // Fallback: charger tout le cache et simuler la pagination
          return await getOfflineSalesPage(pageParam, limit, { search, dateFrom, dateTo, paymentMethod, agentCode, status });
        }
      } else {
        // Mode offline
        return await getOfflineSalesPage(pageParam, limit, { search, dateFrom, dateTo, paymentMethod, agentCode, status });
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

// Helper pour simuler la pagination avec les données en cache
const getOfflineSalesPage = async (page, limit, filters) => {
  let allSales = await getAllItems('sales');
  
  // Appliquer les filtres
  if (filters.search) {
    const searchLower = filters.search.toLowerCase();
    allSales = allSales.filter(s => 
      s.sale_number?.toLowerCase().includes(searchLower) ||
      s.customer_name?.toLowerCase().includes(searchLower)
    );
  }
  if (filters.dateFrom) {
    allSales = allSales.filter(s => new Date(s.created_at) >= new Date(filters.dateFrom));
  }
  if (filters.dateTo) {
    allSales = allSales.filter(s => new Date(s.created_at) <= new Date(filters.dateTo + 'T23:59:59'));
  }
  if (filters.paymentMethod) {
    allSales = allSales.filter(s => s.payment_method === filters.paymentMethod);
  }
  
  // Trier par date décroissante
  allSales.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  
  // Pagination
  const start = (page - 1) * limit;
  const items = allSales.slice(start, start + limit);
  const total = allSales.length;
  const pages = Math.ceil(total / limit);
  
  return { items, total, page, pages, limit };
};

/**
 * Récupérer les ventes avec pagination et filtres
 * Avec support offline
 */
export const useSalesPaginated = (params = {}, options = {}) => {
  const {
    page = 1,
    limit = 20,
    search = '',
    dateFrom = '',
    dateTo = '',
    paymentMethod = '',
    agentCode = '',
    customerId = ''
  } = params;

  return useQuery({
    queryKey: ['sales', 'paginated', { page, limit, search, dateFrom, dateTo, paymentMethod, agentCode, customerId }],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const queryParams = new URLSearchParams();
          queryParams.append('page', page.toString());
          queryParams.append('limit', limit.toString());
          
          if (search) queryParams.append('search', search);
          if (dateFrom) queryParams.append('date_from', dateFrom);
          if (dateTo) queryParams.append('date_to', dateTo);
          if (paymentMethod) queryParams.append('payment_method', paymentMethod);
          if (agentCode) queryParams.append('agent_code', agentCode);
          if (customerId) queryParams.append('customer_id', customerId);

          const response = await api.get(`/sales?${queryParams.toString()}`);
          
          // Mettre en cache
          if (response.data.items && response.data.items.length > 0) {
            try {
              await bulkAddItems('sales', response.data.items);
            } catch (e) {
              console.warn('Cache write failed:', e);
            }
          }
          
          return response.data;
        } catch (error) {
          console.warn('API failed, using cache:', error.message);
          return await getOfflineSalesPage(page, limit, { search, dateFrom, dateTo, paymentMethod, agentCode });
        }
      } else {
        return await getOfflineSalesPage(page, limit, { search, dateFrom, dateTo, paymentMethod, agentCode });
      }
    },
    placeholderData: keepPreviousData,
    staleTime: 30 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer toutes les ventes (ancienne méthode - pour compatibilité)
 * Avec support offline
 */
export const useSales = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.sales,
    queryFn: async () => {
      return await fetchWithOfflineFallback(
        () => api.get('/sales?limit=100'),
        'sales',
        (data) => data.items || data
      );
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    gcTime: 30 * 60 * 1000, // Garder en cache 30 min
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer une vente par ID
 */
export const useSale = (saleId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.sale(saleId),
    queryFn: async () => {
      const response = await api.get(`/sales/${saleId}`);
      return response.data;
    },
    enabled: !!saleId,
    ...options,
  });
};

/**
 * Récupérer l'historique des ventes (opérations)
 */
export const useSalesHistory = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.salesHistory,
    queryFn: async () => {
      const response = await api.get('/sales/history');
      return response.data;
    },
    staleTime: 1 * 60 * 1000, // 1 minute
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer une vente
 */
export const useCreateSale = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (saleData) => {
      const response = await api.post('/sales', saleData);
      return response.data;
    },
    onSuccess: (newSale) => {
      // Invalider les queries liées
      queryClient.invalidateQueries({ queryKey: queryKeys.sales });
      queryClient.invalidateQueries({ queryKey: queryKeys.salesHistory });
      queryClient.invalidateQueries({ queryKey: queryKeys.products }); // Stock mis à jour
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboardStats });
      
      toast.success('Vente enregistrée avec succès', {
        description: `N° ${newSale.sale_number}`,
      });
    },
    onError: (error) => {
      toast.error('Erreur lors de l\'enregistrement de la vente', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Ventes du jour
 */
export const useTodaySales = () => {
  const { data: sales = [], ...rest } = useSales();
  
  const today = new Date().toDateString();
  const todaySales = sales.filter(
    (sale) => new Date(sale.created_at).toDateString() === today
  );

  return { 
    data: todaySales, 
    total: todaySales.reduce((sum, sale) => sum + sale.total_amount, 0),
    count: todaySales.length,
    ...rest 
  };
};

/**
 * Rechercher des ventes
 */
export const useSaleSearch = (filters = {}) => {
  const { data: sales = [], ...rest } = useSales();
  const { search, dateFrom, dateTo, agent } = filters;

  const filteredSales = sales.filter((sale) => {
    // Recherche par numéro, client, agent
    const matchesSearch = !search || 
      sale.sale_number?.toLowerCase().includes(search.toLowerCase()) ||
      sale.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
      sale.created_by?.toLowerCase().includes(search.toLowerCase());

    // Filtre par date
    const saleDate = new Date(sale.created_at);
    const matchesDateFrom = !dateFrom || saleDate >= new Date(dateFrom);
    const matchesDateTo = !dateTo || saleDate <= new Date(dateTo + 'T23:59:59');

    // Filtre par agent
    const matchesAgent = !agent || sale.created_by === agent;

    return matchesSearch && matchesDateFrom && matchesDateTo && matchesAgent;
  });

  return { data: filteredSales, ...rest };
};

/**
 * Statistiques des ventes
 */
export const useSalesStats = () => {
  const { data: sales = [], isLoading } = useSales();

  if (isLoading) return { isLoading: true };

  const today = new Date().toDateString();
  const thisMonth = new Date().getMonth();
  const thisYear = new Date().getFullYear();

  const todaySales = sales.filter(
    (s) => new Date(s.created_at).toDateString() === today
  );
  const monthSales = sales.filter((s) => {
    const d = new Date(s.created_at);
    return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
  });

  return {
    isLoading: false,
    today: {
      count: todaySales.length,
      total: todaySales.reduce((sum, s) => sum + s.total_amount, 0),
    },
    month: {
      count: monthSales.length,
      total: monthSales.reduce((sum, s) => sum + s.total_amount, 0),
    },
    all: {
      count: sales.length,
      total: sales.reduce((sum, s) => sum + s.total_amount, 0),
    },
  };
};

export default {
  useSales,
  useSalesPaginated,
  useSalesInfinite,
  useSale,
  useSalesHistory,
  useCreateSale,
  useTodaySales,
  useSaleSearch,
  useSalesStats,
};
