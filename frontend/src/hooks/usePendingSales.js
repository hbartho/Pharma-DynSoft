import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// Récupérer toutes les ventes en attente
export const usePendingSales = (status = 'pending') => {
  return useQuery({
    queryKey: ['pending-sales', status],
    queryFn: async () => {
      const response = await api.get(`/pending-sales?status=${status}`);
      return response.data;
    },
    refetchInterval: 30000, // Rafraîchir toutes les 30 secondes
  });
};

// Récupérer le nombre de ventes en attente
export const usePendingSalesCount = () => {
  return useQuery({
    queryKey: ['pending-sales-count'],
    queryFn: async () => {
      const response = await api.get('/pending-sales/count');
      return response.data;
    },
    refetchInterval: 30000,
  });
};

// Récupérer une vente en attente par ID
export const usePendingSale = (pendingId) => {
  return useQuery({
    queryKey: ['pending-sale', pendingId],
    queryFn: async () => {
      const response = await api.get(`/pending-sales/${pendingId}`);
      return response.data;
    },
    enabled: !!pendingId,
  });
};

// Créer une vente en attente
export const useCreatePendingSale = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (saleData) => {
      const response = await api.post('/pending-sales', saleData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-sales'] });
      queryClient.invalidateQueries({ queryKey: ['pending-sales-count'] });
    },
  });
};

// Mettre à jour une vente en attente
export const useUpdatePendingSale = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ pendingId, data }) => {
      const response = await api.put(`/pending-sales/${pendingId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-sales'] });
    },
  });
};

// Annuler une vente en attente
export const useCancelPendingSale = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (pendingId) => {
      const response = await api.delete(`/pending-sales/${pendingId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-sales'] });
      queryClient.invalidateQueries({ queryKey: ['pending-sales-count'] });
    },
  });
};

// Finaliser une vente en attente (la marquer comme prête)
export const useCompletePendingSale = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ pendingId, paymentData }) => {
      const response = await api.post(`/pending-sales/${pendingId}/complete`, null, {
        params: paymentData
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-sales'] });
      queryClient.invalidateQueries({ queryKey: ['pending-sales-count'] });
    },
  });
};
