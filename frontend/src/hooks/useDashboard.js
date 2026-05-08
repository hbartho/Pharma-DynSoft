/**
 * React Query Hooks - Dashboard
 * Hooks pour les données du tableau de bord avec cache intelligent et support offline
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { getAllItems } from '../services/indexedDB';

// ============================================
// Helper pour calculs offline du dashboard
// ============================================

const calculateOfflineDashboardStats = async () => {
  const sales = await getAllItems('sales') || [];
  const products = await getAllItems('products') || [];
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const todaySales = sales.filter(s => {
    const saleDate = new Date(s.created_at);
    saleDate.setHours(0, 0, 0, 0);
    return saleDate.getTime() === today.getTime() && s.status !== 'CANCELLED';
  });
  
  const todayRevenue = todaySales.reduce((sum, s) => sum + (s.total || 0), 0);
  const lowStockCount = products.filter(p => (p.stock || 0) <= (p.min_stock || 10)).length;
  const totalStockValue = products.reduce((sum, p) => sum + ((p.stock || 0) * (p.purchase_price || p.price * 0.7 || 0)), 0);
  
  return {
    today_sales_count: todaySales.length,
    today_revenue: todayRevenue,
    total_products: products.length,
    low_stock_count: lowStockCount,
    pending_prescriptions: 0,
    total_stock_value: Math.round(totalStockValue * 100) / 100,
    stock_valuation_method: 'weighted_average',
    _offline: true
  };
};

const calculateOfflineWeeklyStats = async () => {
  const sales = await getAllItems('sales') || [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  const dailyStats = [];
  for (let i = 6; i >= 0; i--) {
    const day = new Date(today);
    day.setDate(day.getDate() - i);
    const dayStr = day.toISOString().split('T')[0];
    
    const daySales = sales.filter(s => {
      const saleDate = new Date(s.created_at);
      return saleDate.toISOString().split('T')[0] === dayStr && s.status !== 'CANCELLED';
    });
    
    dailyStats.push({
      date: dayStr,
      sales_count: daySales.length,
      revenue: daySales.reduce((sum, s) => sum + (s.total || 0), 0)
    });
  }
  
  return {
    period: '7 derniers jours',
    daily_stats: dailyStats,
    total_sales: sales.filter(s => s.status !== 'CANCELLED').length,
    total_revenue: sales.filter(s => s.status !== 'CANCELLED').reduce((sum, s) => sum + (s.total || 0), 0),
    _offline: true
  };
};

const calculateOfflineSalesByPayment = async (selectedDate) => {
  const sales = await getAllItems('sales') || [];
  
  let targetDate;
  if (selectedDate) {
    targetDate = new Date(selectedDate);
  } else {
    targetDate = new Date();
  }
  targetDate.setHours(0, 0, 0, 0);
  
  const daySales = sales.filter(s => {
    const saleDate = new Date(s.created_at);
    saleDate.setHours(0, 0, 0, 0);
    return saleDate.getTime() === targetDate.getTime() && s.status !== 'CANCELLED';
  });
  
  const byPayment = {};
  let totalDiscount = 0;
  let discountCount = 0;
  
  const LABELS = {
    'cash': 'Espèces',
    'card': 'Carte bancaire',
    'check': 'Chèque',
    'orange_money': 'Orange Money',
    'mtn_money': 'MTN Money',
    'credit': 'Crédit/Dette'
  };
  
  daySales.forEach(sale => {
    if (sale.discount > 0) {
      totalDiscount += sale.discount;
      discountCount++;
    }
    
    const method = sale.payment_method || 'cash';
    if (!byPayment[method]) {
      byPayment[method] = { method, label: LABELS[method] || method, count: 0, total: 0, full_sales_count: 0, partial_sales_count: 0 };
    }
    byPayment[method].total += sale.total || 0;
    byPayment[method].full_sales_count += 1;
    byPayment[method].count += 1;
  });
  
  return {
    date: targetDate.toISOString().split('T')[0],
    total_sales: daySales.length,
    total_revenue: daySales.reduce((sum, s) => sum + (s.total || 0), 0),
    by_payment_method: Object.values(byPayment),
    discount_info: { total_discount: totalDiscount, discount_count: discountCount },
    _offline: true
  };
};

// ============================================
// Queries
// ============================================

/**
 * Récupérer les statistiques du dashboard
 * Avec support offline
 */
export const useDashboardStats = (options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get('/reports/dashboard');
          return response.data;
        } catch (error) {
          console.warn('Dashboard API failed, calculating from cache:', error.message);
          return await calculateOfflineDashboardStats();
        }
      } else {
        console.log('Offline: calculating dashboard from cache');
        return await calculateOfflineDashboardStats();
      }
    },
    staleTime: 1 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer les ventes récentes pour le graphique
 * Avec support offline
 */
export const useDashboardSales = (days = 7, options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'sales', days],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get('/reports/weekly');
          return response.data;
        } catch (error) {
          console.warn('Weekly API failed, calculating from cache:', error.message);
          return await calculateOfflineWeeklyStats();
        }
      } else {
        return await calculateOfflineWeeklyStats();
      }
    },
    staleTime: 2 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer les approvisionnements en attente
 */
export const usePendingSuppliesCount = (options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'pending-supplies'],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get('/supplies?status=pending');
          return response.data.length;
        } catch (error) {
          const supplies = await getAllItems('supplies') || [];
          return supplies.filter(s => s.status === 'pending').length;
        }
      } else {
        const supplies = await getAllItems('supplies') || [];
        return supplies.filter(s => s.status === 'pending').length;
      }
    },
    staleTime: 2 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer les mouvements de stock
 */
export const useStockMovements = (limit = 20, options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'stock-movements', limit],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get(`/stock/movements?limit=${limit}`);
          return response.data;
        } catch (error) {
          return [];
        }
      }
      return [];
    },
    staleTime: 1 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer l'historique des prix
 */
export const usePriceHistory = (limit = 20, options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'price-history', limit],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const response = await api.get(`/prices/history?limit=${limit}`);
          return response.data;
        } catch (error) {
          return [];
        }
      }
      return [];
    },
    staleTime: 2 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Récupérer les ventes par mode de paiement pour une date spécifique
 * Avec support offline
 */
export const useSalesByPayment = (selectedDate = null, options = {}) => {
  return useQuery({
    queryKey: ['dashboard', 'sales-by-payment', selectedDate],
    queryFn: async () => {
      if (navigator.onLine) {
        try {
          const params = selectedDate ? `?date=${selectedDate}` : '';
          const response = await api.get(`/reports/today-sales-by-payment${params}`);
          return response.data;
        } catch (error) {
          console.warn('Sales by payment API failed, calculating from cache:', error.message);
          return await calculateOfflineSalesByPayment(selectedDate);
        }
      } else {
        return await calculateOfflineSalesByPayment(selectedDate);
      }
    },
    staleTime: 1 * 60 * 1000,
    retry: navigator.onLine ? 1 : 0,
    ...options,
  });
};

/**
 * Hook combiné pour toutes les données du dashboard
 */
export const useDashboardData = (salesDate = null) => {
  const statsQuery = useDashboardStats();
  const salesQuery = useDashboardSales(7);
  const pendingSuppliesQuery = usePendingSuppliesCount();
  const stockMovementsQuery = useStockMovements(20);
  const priceHistoryQuery = usePriceHistory(20);
  const salesByPaymentQuery = useSalesByPayment(salesDate);

  const isLoading = 
    statsQuery.isLoading || 
    salesQuery.isLoading || 
    pendingSuppliesQuery.isLoading ||
    stockMovementsQuery.isLoading ||
    priceHistoryQuery.isLoading ||
    salesByPaymentQuery.isLoading;

  // Transformer les données de ventes pour le graphique
  const salesChartData = salesQuery.data?.daily_stats
    ? (Array.isArray(salesQuery.data.daily_stats) 
        ? salesQuery.data.daily_stats 
        : Object.entries(salesQuery.data.daily_stats).map(([date, data]) => ({ date, ...data }))
      )
        .map((item) => ({
          date: item.date,
          dateFormatted: new Date(item.date).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          revenue: item.revenue,
          count: item.sales_count || item.count || 0,
        }))
        .sort((a, b) => new Date(a.date) - new Date(b.date))
        .map(({ dateFormatted, revenue, count }) => ({
          date: dateFormatted,
          revenue,
          count,
        }))
    : [];

  // Transformer les mouvements de stock pour le graphique
  const stockMovementsData = stockMovementsQuery.data
    ? stockMovementsQuery.data
        .slice(0, 10)
        .reverse()
        .map((mov) => ({
          product: mov.product_name?.substring(0, 15) || 'N/A',
          quantity: mov.movement_quantity,
          type: mov.movement_type,
          stockAfter: mov.stock_after,
          date: new Date(mov.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
        }))
    : [];

  // Transformer l'historique des prix pour le graphique
  const priceHistoryData = priceHistoryQuery.data
    ? priceHistoryQuery.data
        .slice(0, 10)
        .reverse()
        .map((price) => ({
          product: price.product_name?.substring(0, 15) || 'N/A',
          prixAchat: price.prix_appro || 0,
          prixVente: price.prix_vente_prod || 0,
          date: new Date(price.created_at).toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
          modifiedBy: price.created_by || 'N/A',
        }))
    : [];

  // Statistiques des mouvements de stock
  const stockStats = {
    totalEntries: stockMovementsData.filter(m => m.quantity > 0).reduce((sum, m) => sum + m.quantity, 0),
    totalExits: Math.abs(stockMovementsData.filter(m => m.quantity < 0).reduce((sum, m) => sum + m.quantity, 0)),
    recentCount: stockMovementsData.length,
  };

  // Données des ventes par mode de paiement pour la date sélectionnée
  // L'API retourne by_payment_method et total_sales, on normalise les noms
  const rawSalesByPayment = salesByPaymentQuery.data || {};
  const salesByPayment = {
    date: rawSalesByPayment.date || new Date().toISOString(),
    total_count: rawSalesByPayment.total_sales || 0,
    total_revenue: rawSalesByPayment.total_revenue || 0,
    by_payment: rawSalesByPayment.by_payment_method || [],
    discount_info: rawSalesByPayment.discount_info || { total_discount: 0, discount_count: 0 }
  };

  return {
    stats: statsQuery.data || {
      today_sales_count: 0,
      today_revenue: 0,
      total_products: 0,
      low_stock_count: 0,
      pending_prescriptions: 0,
      total_stock_value: 0,
      stock_valuation_method: 'weighted_average',
    },
    pendingSupplies: pendingSuppliesQuery.data || 0,
    salesChartData,
    stockMovementsData,
    priceHistoryData,
    stockStats,
    salesByPayment,
    isLoading,
    isSalesByPaymentLoading: salesByPaymentQuery.isLoading,
  };
};

export default {
  useDashboardStats,
  useDashboardSales,
  usePendingSuppliesCount,
  useStockMovements,
  usePriceHistory,
  useSalesByPayment,
  useDashboardData,
};
