/**
 * React Query Hooks - Retours
 * Hooks pour la gestion des retours avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les retours
 */
export const useReturns = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.returns,
    queryFn: async () => {
      const response = await api.get('/returns');
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options,
  });
};

/**
 * Récupérer l'historique complet (ventes + retours)
 */
export const useOperationsHistory = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.salesHistory,
    queryFn: async () => {
      // Récupérer les ventes et les retours en parallèle
      const [salesResponse, returnsResponse] = await Promise.all([
        api.get('/sales?limit=50'),
        api.get('/returns/history')
      ]);
      
      // L'API sales retourne { items: [], total, ... } 
      const salesData = salesResponse.data;
      const sales = Array.isArray(salesData) ? salesData : (salesData?.items || []);
      const returns = returnsResponse.data || [];
      
      // Transformer les ventes en format opération (avec les champs attendus par le modal)
      const salesOperations = sales.map(sale => ({
        id: sale.id,
        type: 'sale',
        operation_number: sale.sale_number,
        reference: sale.sale_number,
        amount: sale.total_amount || sale.total,
        items_count: sale.items?.length || sale.items_count || 0,
        employee_code: sale.agent_code,
        agent_code: sale.agent_code,
        user_name: sale.agent_name,
        agent_name: sale.agent_name,
        user_role: sale.agent_role,
        customer_name: sale.customer_name,
        payment_method: sale.payment_method,
        date: sale.created_at,
        created_at: sale.created_at
      }));
      
      // Transformer les retours en format opération
      const returnsOperations = returns.map(ret => ({
        id: ret.id,
        type: 'return',
        operation_number: ret.return_number,
        reference: ret.return_number,
        sale_number: ret.sale_number,
        amount: ret.total_refund,
        items_count: ret.items?.length || 0,
        employee_code: ret.agent_code,
        agent_code: ret.agent_code,
        user_name: ret.agent_name,
        agent_name: ret.agent_name,
        reason: ret.reason,
        date: ret.created_at,
        created_at: ret.created_at
      }));
      
      // Combiner et trier par date décroissante
      const allOperations = [...salesOperations, ...returnsOperations].sort((a, b) => {
        const dateA = new Date(a.created_at || 0);
        const dateB = new Date(b.created_at || 0);
        return dateB - dateA;
      });
      
      return allOperations;
    },
    staleTime: 0,
    refetchOnMount: true,
    ...options,
  });
};

/**
 * Récupérer les retours d'une vente spécifique
 */
export const useReturnsBySale = (saleId, options = {}) => {
  return useQuery({
    queryKey: ['returns', 'sale', saleId],
    queryFn: async () => {
      const response = await api.get(`/returns/sale/${saleId}`);
      return response.data;
    },
    enabled: !!saleId,
    ...options,
  });
};

/**
 * Vérifier l'éligibilité au retour
 */
export const useReturnEligibility = (saleId, options = {}) => {
  return useQuery({
    queryKey: ['returns', 'eligibility', saleId],
    queryFn: async () => {
      const response = await api.get(`/returns/check-eligibility/${saleId}`);
      return response.data;
    },
    enabled: !!saleId,
    staleTime: 30 * 1000, // 30 seconds
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un retour
 */
export const useCreateReturn = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (returnData) => {
      const response = await api.post('/returns', returnData);
      return response.data;
    },
    onSuccess: () => {
      // Invalider toutes les données liées
      queryClient.invalidateQueries({ queryKey: queryKeys.returns });
      queryClient.invalidateQueries({ queryKey: queryKeys.sales });
      queryClient.invalidateQueries({ queryKey: queryKeys.salesHistory });
      queryClient.invalidateQueries({ queryKey: queryKeys.products });
      queryClient.invalidateQueries({ queryKey: queryKeys.productAlerts });
      toast.success('Retour effectué avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors du retour', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Rechercher dans l'historique
 */
export const useHistorySearch = (searchTerm = '', type = null) => {
  const { data: history = [], ...rest } = useOperationsHistory();

  const filtered = history.filter((item) => {
    const matchesSearch = !searchTerm || 
      item.operation_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.employee_code?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesType = !type || type === 'all' || item.type === type;

    return matchesSearch && matchesType;
  });

  return { data: filtered, ...rest };
};

/**
 * Statistiques des retours
 */
export const useReturnStats = () => {
  const { data: returns = [], isLoading } = useReturns();

  const stats = {
    totalReturns: returns.length,
    totalRefunded: returns.reduce((sum, r) => sum + (r.total_refund || 0), 0),
    todayReturns: returns.filter(r => {
      const today = new Date().toDateString();
      const returnDate = new Date(r.created_at).toDateString();
      return today === returnDate;
    }).length,
  };

  return { stats, isLoading };
};

export default {
  useReturns,
  useOperationsHistory,
  useReturnsBySale,
  useReturnEligibility,
  useCreateReturn,
  useHistorySearch,
  useReturnStats,
};
