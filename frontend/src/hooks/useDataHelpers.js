import { useState, useCallback, useRef, useEffect } from 'react';
import api from '../services/api';

/**
 * Hook pour gérer les appels API avec cache et état de chargement
 * Évite les appels redondants et gère automatiquement les erreurs
 */
export const useApiData = (endpoint, options = {}) => {
  const {
    cacheKey = endpoint,
    cacheDuration = 5 * 60 * 1000, // 5 minutes par défaut
    autoFetch = true,
    initialData = null,
    transform = (data) => data,
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(autoFetch);
  const [error, setError] = useState(null);
  const lastFetchRef = useRef(null);
  const cacheRef = useRef(new Map());

  const fetchData = useCallback(async (forceRefresh = false) => {
    // Vérifier le cache
    const cached = cacheRef.current.get(cacheKey);
    if (!forceRefresh && cached && (Date.now() - cached.timestamp) < cacheDuration) {
      setData(cached.data);
      setLoading(false);
      return cached.data;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await api.get(endpoint);
      const transformedData = transform(response.data);
      
      // Mettre en cache
      cacheRef.current.set(cacheKey, {
        data: transformedData,
        timestamp: Date.now(),
      });
      
      setData(transformedData);
      lastFetchRef.current = Date.now();
      return transformedData;
    } catch (err) {
      setError(err.message || 'Erreur lors du chargement');
      console.error(`Error fetching ${endpoint}:`, err);
      return null;
    } finally {
      setLoading(false);
    }
  }, [endpoint, cacheKey, cacheDuration, transform]);

  const refresh = useCallback(() => {
    return fetchData(true);
  }, [fetchData]);

  const clearCache = useCallback(() => {
    cacheRef.current.delete(cacheKey);
  }, [cacheKey]);

  useEffect(() => {
    if (autoFetch) {
      fetchData();
    }
  }, [autoFetch, fetchData]);

  return {
    data,
    loading,
    error,
    refresh,
    clearCache,
    fetchData,
  };
};

/**
 * Hook pour gérer les opérations CRUD avec état optimiste
 */
export const useCrudOperations = (baseEndpoint) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const create = useCallback(async (data) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post(baseEndpoint, data);
      return { success: true, data: response.data };
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return { success: false, error: err.response?.data?.detail || err.message };
    } finally {
      setLoading(false);
    }
  }, [baseEndpoint]);

  const update = useCallback(async (id, data) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.put(`${baseEndpoint}/${id}`, data);
      return { success: true, data: response.data };
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return { success: false, error: err.response?.data?.detail || err.message };
    } finally {
      setLoading(false);
    }
  }, [baseEndpoint]);

  const remove = useCallback(async (id) => {
    setLoading(true);
    setError(null);
    try {
      await api.delete(`${baseEndpoint}/${id}`);
      return { success: true };
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
      return { success: false, error: err.response?.data?.detail || err.message };
    } finally {
      setLoading(false);
    }
  }, [baseEndpoint]);

  return {
    create,
    update,
    remove,
    loading,
    error,
    clearError: () => setError(null),
  };
};

/**
 * Hook pour le debouncing des recherches
 */
export const useDebounce = (value, delay = 300) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
};

/**
 * Hook pour la pagination
 */
export const usePagination = (items, itemsPerPage = 10) => {
  const [currentPage, setCurrentPage] = useState(1);

  const totalPages = Math.ceil((items?.length || 0) / itemsPerPage);
  
  const paginatedItems = items?.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  ) || [];

  const goToPage = useCallback((page) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)));
  }, [totalPages]);

  const nextPage = useCallback(() => {
    goToPage(currentPage + 1);
  }, [currentPage, goToPage]);

  const prevPage = useCallback(() => {
    goToPage(currentPage - 1);
  }, [currentPage, goToPage]);

  // Reset to page 1 when items change significantly
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [currentPage, totalPages]);

  return {
    currentPage,
    totalPages,
    paginatedItems,
    goToPage,
    nextPage,
    prevPage,
    hasNextPage: currentPage < totalPages,
    hasPrevPage: currentPage > 1,
  };
};

/**
 * Hook pour gérer les filtres et la recherche
 */
export const useFilters = (initialFilters = {}) => {
  const [filters, setFilters] = useState(initialFilters);

  const updateFilter = useCallback((key, value) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(initialFilters);
  }, [initialFilters]);

  const clearFilter = useCallback((key) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      delete newFilters[key];
      return newFilters;
    });
  }, []);

  const applyFilters = useCallback((items, filterFn) => {
    if (!items) return [];
    return items.filter(item => filterFn(item, filters));
  }, [filters]);

  return {
    filters,
    setFilters,
    updateFilter,
    resetFilters,
    clearFilter,
    applyFilters,
    hasActiveFilters: Object.values(filters).some(v => v !== '' && v !== null && v !== undefined),
  };
};

/**
 * Hook pour le tri des données
 */
export const useSort = (initialSortKey = '', initialSortOrder = 'asc') => {
  const [sortKey, setSortKey] = useState(initialSortKey);
  const [sortOrder, setSortOrder] = useState(initialSortOrder);

  const toggleSort = useCallback((key) => {
    if (sortKey === key) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  }, [sortKey]);

  const sortItems = useCallback((items) => {
    if (!items || !sortKey) return items;
    
    return [...items].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      
      const comparison = aVal < bVal ? -1 : 1;
      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [sortKey, sortOrder]);

  return {
    sortKey,
    sortOrder,
    toggleSort,
    sortItems,
    setSortKey,
    setSortOrder,
  };
};

export default {
  useApiData,
  useCrudOperations,
  useDebounce,
  usePagination,
  useFilters,
  useSort,
};
