/**
 * Configuration React Query
 * Client et options par défaut pour la gestion des requêtes API
 */

import { QueryClient } from '@tanstack/react-query';

// Configuration par défaut
const defaultOptions = {
  queries: {
    // Temps pendant lequel les données sont considérées "fraîches"
    staleTime: 5 * 60 * 1000, // 5 minutes
    
    // Temps de cache des données inactives
    gcTime: 30 * 60 * 1000, // 30 minutes (anciennement cacheTime)
    
    // Nombre de tentatives en cas d'erreur
    retry: 2,
    
    // Délai entre les tentatives (exponentiel)
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    
    // Refetch quand la fenêtre reprend le focus
    refetchOnWindowFocus: true,
    
    // Refetch quand la connexion est rétablie
    refetchOnReconnect: true,
    
    // Ne pas refetch automatiquement au mount si les données sont fraîches
    refetchOnMount: true,
  },
  mutations: {
    // Nombre de tentatives pour les mutations
    retry: 1,
    
    // Callback global pour les erreurs de mutation
    onError: (error) => {
      console.error('Mutation error:', error);
    },
  },
};

// Créer le client
export const queryClient = new QueryClient({
  defaultOptions,
});

// Clés de query standardisées
export const queryKeys = {
  // Products
  products: ['products'],
  product: (id) => ['products', id],
  productAlerts: ['products', 'alerts'],
  
  // Categories
  categories: ['categories'],
  category: (id) => ['categories', id],
  
  // Customers
  customers: ['customers'],
  customer: (id) => ['customers', id],
  
  // Suppliers
  suppliers: ['suppliers'],
  supplier: (id) => ['suppliers', id],
  
  // Sales
  sales: ['sales'],
  sale: (id) => ['sales', id],
  salesHistory: ['sales', 'history'],
  
  // Supplies
  supplies: ['supplies'],
  supply: (id) => ['supplies', id],
  
  // Returns
  returns: ['returns'],
  returnItem: (id) => ['returns', id],
  
  // Units
  units: ['units'],
  
  // Settings
  settings: ['settings'],
  
  // Users
  users: ['users'],
  user: (id) => ['users', id],
  
  // Dashboard
  dashboard: ['dashboard'],
  dashboardStats: ['dashboard', 'stats'],
  stockHistory: (productId) => ['stock-history', productId],
  priceHistory: (productId) => ['price-history', productId],
  
  // Stock
  stockValuation: ['stock', 'valuation'],
  stockMovements: ['stock', 'movements'],
};

// Helper pour invalider plusieurs queries
export const invalidateQueries = async (keys) => {
  const promises = keys.map((key) => queryClient.invalidateQueries({ queryKey: key }));
  await Promise.all(promises);
};

// Helper pour précharger des données
export const prefetchQuery = async (queryKey, queryFn) => {
  await queryClient.prefetchQuery({
    queryKey,
    queryFn,
    staleTime: 5 * 60 * 1000,
  });
};

export default queryClient;
