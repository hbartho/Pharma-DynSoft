import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// Récupérer les motifs de perte
export const useLossReasons = () => {
  return useQuery({
    queryKey: ['loss-reasons'],
    queryFn: async () => {
      const response = await api.get('/stock/losses/reasons');
      return response.data;
    },
    staleTime: 1000 * 60 * 60, // 1 heure
  });
};

// Récupérer les pertes en attente
export const usePendingLosses = () => {
  return useQuery({
    queryKey: ['pending-losses'],
    queryFn: async () => {
      const response = await api.get('/stock/losses/pending');
      return response.data;
    },
  });
};

// Récupérer l'historique des pertes
export const useLossesHistory = (filters = {}) => {
  const { status, reason, productId, dateFrom, dateTo, limit = 50 } = filters;
  
  return useQuery({
    queryKey: ['losses-history', status, reason, productId, dateFrom, dateTo, limit],
    queryFn: async () => {
      const params = { limit };
      if (status) params.status = status;
      if (reason) params.reason = reason;
      if (productId) params.product_id = productId;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      
      const response = await api.get('/stock/losses/history', { params });
      return response.data;
    },
  });
};

// Statistiques des pertes
export const useLossesStats = (period = 'month') => {
  return useQuery({
    queryKey: ['losses-stats', period],
    queryFn: async () => {
      const response = await api.get('/stock/losses/stats', { params: { period } });
      return response.data;
    },
  });
};

// Déclarer une perte
export const useDeclareLoss = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ productId, quantity, reason, reasonDetails, lotNumber, notes }) => {
      const params = new URLSearchParams({
        product_id: productId,
        quantity: quantity.toString(),
        reason: reason,
      });
      if (reasonDetails) params.append('reason_details', reasonDetails);
      if (lotNumber) params.append('lot_number', lotNumber);
      if (notes) params.append('notes', notes);
      
      const response = await api.post(`/stock/losses?${params.toString()}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-losses'] });
      queryClient.invalidateQueries({ queryKey: ['losses-history'] });
      queryClient.invalidateQueries({ queryKey: ['losses-stats'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['stock-movements'] });
    },
  });
};

// Valider une perte (admin)
export const useValidateLoss = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ lossId, action, rejectionReason }) => {
      const params = new URLSearchParams({ action });
      if (rejectionReason) params.append('rejection_reason', rejectionReason);
      
      const response = await api.post(`/stock/losses/${lossId}/validate?${params.toString()}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-losses'] });
      queryClient.invalidateQueries({ queryKey: ['losses-history'] });
      queryClient.invalidateQueries({ queryKey: ['losses-stats'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
      queryClient.invalidateQueries({ queryKey: ['stock-movements'] });
    },
  });
};

// Récupérer les mouvements de stock
export const useStockMovements = (filters = {}) => {
  const { productId, movementType, limit = 100 } = filters;
  
  return useQuery({
    queryKey: ['stock-movements', productId, movementType, limit],
    queryFn: async () => {
      const params = { limit };
      if (productId) params.product_id = productId;
      if (movementType) params.movement_type = movementType;
      
      const response = await api.get('/stock/movements', { params });
      return response.data;
    },
  });
};

// Historique des mouvements d'un produit
export const useProductMovements = (productId, limit = 50) => {
  return useQuery({
    queryKey: ['product-movements', productId, limit],
    queryFn: async () => {
      const response = await api.get(`/stock/movements/${productId}`, { params: { limit } });
      return response.data;
    },
    enabled: !!productId,
  });
};
