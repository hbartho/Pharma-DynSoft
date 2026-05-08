/**
 * React Query Hooks - Payment Methods (Modes de paiement)
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// ============== QUERIES ==============

/**
 * Récupérer tous les modes de paiement
 */
export const usePaymentMethods = (activeOnly = false) => {
  return useQuery({
    queryKey: ['paymentMethods', { activeOnly }],
    queryFn: async () => {
      const params = activeOnly ? '?active_only=true' : '';
      const response = await api.get(`/payment-methods${params}`);
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Récupérer un mode de paiement par ID
 */
export const usePaymentMethod = (methodId) => {
  return useQuery({
    queryKey: ['paymentMethod', methodId],
    queryFn: async () => {
      const response = await api.get(`/payment-methods/${methodId}`);
      return response.data;
    },
    enabled: !!methodId,
  });
};

/**
 * Récupérer les paiements d'une vente
 */
export const useSalePayments = (saleId) => {
  return useQuery({
    queryKey: ['salePayments', saleId],
    queryFn: async () => {
      const response = await api.get(`/payment-methods/sale/${saleId}/payments`);
      return response.data;
    },
    enabled: !!saleId,
  });
};

// ============== MUTATIONS ==============

/**
 * Créer un mode de paiement
 */
export const useCreatePaymentMethod = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/payment-methods', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paymentMethods'] });
    },
  });
};

/**
 * Mettre à jour un mode de paiement
 */
export const useUpdatePaymentMethod = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, data }) => {
      const response = await api.put(`/payment-methods/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paymentMethods'] });
    },
  });
};

/**
 * Supprimer un mode de paiement
 */
export const useDeletePaymentMethod = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (id) => {
      const response = await api.delete(`/payment-methods/${id}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['paymentMethods'] });
    },
  });
};

/**
 * Créer un paiement pour une vente
 */
export const useCreateSalePayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/payment-methods/sale/payment', data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['salePayments', variables.sale_id] });
      queryClient.invalidateQueries({ queryKey: ['sales'] });
    },
  });
};

export default {
  usePaymentMethods,
  usePaymentMethod,
  useSalePayments,
  useCreatePaymentMethod,
  useUpdatePaymentMethod,
  useDeletePaymentMethod,
  useCreateSalePayment,
};
