/**
 * React Query Hooks - Ventes
 * Hooks pour la gestion des ventes avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer toutes les ventes
 */
export const useSales = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.sales,
    queryFn: async () => {
      const response = await api.get('/sales');
      return response.data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
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
  useSale,
  useSalesHistory,
  useCreateSale,
  useTodaySales,
  useSaleSearch,
  useSalesStats,
};
