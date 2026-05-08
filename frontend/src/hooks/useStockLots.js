/**
 * React Query Hooks - Stock Lots (Gestion des prix des lots)
 * Admin only
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { toast } from 'sonner';

// Query keys
export const stockLotKeys = {
  all: ['stock-lots'],
  bySupply: (supplyId) => ['stock-lots', 'supply', supplyId],
  byProduct: (productId) => ['stock-lots', 'product', productId],
};

/**
 * Get all active stock lots
 */
export const useStockLots = (options = {}) => {
  const { productId, supplyId, activeOnly = true, refetchInterval = false } = options;
  
  return useQuery({
    queryKey: [...stockLotKeys.all, { productId, supplyId, activeOnly }],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (productId) params.append('product_id', productId);
      if (supplyId) params.append('supply_id', supplyId);
      params.append('active_only', activeOnly.toString());
      
      const response = await api.get(`/stock-lots?${params.toString()}`);
      return response.data;
    },
    refetchInterval: refetchInterval, // Auto-refresh interval in ms
    refetchIntervalInBackground: false, // Don't refresh when tab is not active
  });
};

/**
 * Get stock lots for a specific supply
 */
export const useStockLotsBySupply = (supplyId) => {
  return useQuery({
    queryKey: stockLotKeys.bySupply(supplyId),
    queryFn: async () => {
      const response = await api.get(`/stock-lots/by-supply/${supplyId}`);
      return response.data;
    },
    enabled: !!supplyId,
  });
};

/**
 * Update a single stock lot
 */
export const useUpdateStockLot = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ lotId, data }) => {
      const response = await api.put(`/stock-lots/${lotId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: stockLotKeys.all });
      toast.success('Prix du lot mis à jour');
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la mise à jour', {
        description: errorMessage,
      });
    },
  });
};

/**
 * Bulk update multiple stock lots
 */
export const useBulkUpdateStockLots = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (updates) => {
      const response = await api.put('/stock-lots/bulk-update', updates);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: stockLotKeys.all });
      toast.success(`${data.updated_count} lot(s) mis à jour`);
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la mise à jour', {
        description: errorMessage,
      });
    },
  });
};

export default {
  useStockLots,
  useStockLotsBySupply,
  useUpdateStockLot,
  useBulkUpdateStockLots,
};
