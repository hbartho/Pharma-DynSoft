/**
 * React Query Hooks - Rapports
 * Hooks pour la gestion des rapports avec cache intelligent
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';

// ============================================
// Queries
// ============================================

/**
 * Récupérer les rapports de ventes (période start/end, sinon 30 derniers jours)
 */
export const useSalesReport = (range = null, options = {}) => {
  return useQuery({
    queryKey: ['reports', 'sales', range?.start, range?.end],
    queryFn: async () => {
      const params = range?.start ? { start_date: range.start, end_date: range.end } : { days: 30 };
      const response = await api.get('/reports/sales', { params });
      return response.data;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    ...options,
  });
};

/**
 * Transformer les données pour les graphiques
 */
export const useChartData = (range = null) => {
  const { data: salesData, isLoading, isError } = useSalesReport(range);

  const chartData = salesData
    ? Object.entries(salesData.daily_stats)
        .map(([date, data]) => ({
          date,
          dateFormatted: new Date(date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          revenue: Math.round(data.revenue * 100) / 100,
          count: data.count,
        }))
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .map(({ dateFormatted, revenue, count }) => ({
          date: dateFormatted,
          revenue,
          count,
        }))
    : [];

  return {
    salesData,
    chartData,
    isLoading,
    isError,
  };
};

export default {
  useSalesReport,
  useChartData,
};
