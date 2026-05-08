import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';

// ============== DASHBOARD & STATISTIQUES ==============

export const useDebtDashboard = (period = null) => {
  return useQuery({
    queryKey: ['debt-dashboard', period],
    queryFn: async () => {
      const params = {};
      if (period) params.period = period;
      const response = await api.get('/debts/dashboard', { params });
      return response.data;
    },
  });
};

export const useCustomersDebtSummary = (onlyWithDebt = false) => {
  return useQuery({
    queryKey: ['customers-debt-summary', onlyWithDebt],
    queryFn: async () => {
      const response = await api.get('/debts/customers-summary', {
        params: { only_with_debt: onlyWithDebt }
      });
      return response.data;
    },
  });
};

// ============== DETTES ==============

export const useDebts = (customerId = null, status = null) => {
  return useQuery({
    queryKey: ['debts', customerId, status],
    queryFn: async () => {
      const params = {};
      if (customerId) params.customer_id = customerId;
      if (status) params.status = status;
      const response = await api.get('/debts', { params });
      return response.data;
    },
  });
};

export const useDebt = (debtId) => {
  return useQuery({
    queryKey: ['debt', debtId],
    queryFn: async () => {
      const response = await api.get(`/debts/${debtId}`);
      return response.data;
    },
    enabled: !!debtId,
  });
};

export const useDebtPayments = (debtId) => {
  return useQuery({
    queryKey: ['debt-payments', debtId],
    queryFn: async () => {
      const response = await api.get(`/debts/${debtId}/payments`);
      return response.data;
    },
    enabled: !!debtId,
  });
};

export const useCustomerDebts = (customerId, includePaid = false) => {
  return useQuery({
    queryKey: ['customer-debts', customerId, includePaid],
    queryFn: async () => {
      const response = await api.get(`/debts/customer/${customerId}`, {
        params: { include_paid: includePaid }
      });
      return response.data;
    },
    enabled: !!customerId,
  });
};

export const useCustomerAvailableCredit = (customerId) => {
  return useQuery({
    queryKey: ['customer-credit', customerId],
    queryFn: async () => {
      const response = await api.get(`/debts/customer/${customerId}/available-credit`);
      return response.data;
    },
    enabled: !!customerId,
  });
};

// ============== REMBOURSEMENTS ==============

export const useCreateDebtPayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (paymentData) => {
      const response = await api.post('/debts/payment', paymentData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debts'] });
      queryClient.invalidateQueries({ queryKey: ['debt-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['customers-debt-summary'] });
      queryClient.invalidateQueries({ queryKey: ['customer-debts'] });
      queryClient.invalidateQueries({ queryKey: ['customer-credit'] });
      queryClient.invalidateQueries({ queryKey: ['customers'] });
    },
  });
};

export const useCreateBulkPayment = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ customerId, amount, paymentMethod, paymentDetails, notes }) => {
      const response = await api.post('/debts/payment/bulk', {
        customer_id: customerId,
        amount: amount,
        payment_method: paymentMethod,
        payment_details: paymentDetails || null,
        notes: notes || null
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debts'] });
      queryClient.invalidateQueries({ queryKey: ['debt-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['customers-debt-summary'] });
      queryClient.invalidateQueries({ queryKey: ['customer-debts'] });
      queryClient.invalidateQueries({ queryKey: ['customer-credit'] });
      queryClient.invalidateQueries({ queryKey: ['customers'] });
      queryClient.invalidateQueries({ queryKey: ['payments-history'] });
    },
  });
};

export const useWriteOffDebt = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ debtId, reason }) => {
      const response = await api.post(`/debts/${debtId}/write-off`, { reason });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['debts'] });
      queryClient.invalidateQueries({ queryKey: ['debt-dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['customers-debt-summary'] });
      queryClient.invalidateQueries({ queryKey: ['customer-debts'] });
      queryClient.invalidateQueries({ queryKey: ['customer-credit'] });
      queryClient.invalidateQueries({ queryKey: ['payments-history'] });
      queryClient.invalidateQueries({ queryKey: ['customers'] }); // Rafraîchir la liste des clients (seuil crédit + dette)
    },
  });
};

export const usePaymentsHistory = (filters = {}) => {
  const { customerId, paymentMethod, dateFrom, dateTo, limit = 50 } = filters;
  
  return useQuery({
    queryKey: ['payments-history', customerId, paymentMethod, dateFrom, dateTo, limit],
    queryFn: async () => {
      const params = { limit };
      if (customerId) params.customer_id = customerId;
      if (paymentMethod) params.payment_method = paymentMethod;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const response = await api.get('/debts/payments/history', { params });
      return response.data;
    },
  });
};
