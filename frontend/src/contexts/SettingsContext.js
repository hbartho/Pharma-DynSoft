import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import api from '../services/api';
import { formatCurrency, getCurrencySymbol } from '../services/currencyService';

const SettingsContext = createContext();

// Default settings pour utilisation hors contexte
const DEFAULT_SETTINGS = {
  currency: 'GNF',
  stock_valuation_method: 'weighted_average',
  pharmacy_name: '',
  low_stock_threshold: 10,
};

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    // Retourner des valeurs par défaut si le contexte n'est pas disponible
    return {
      settings: DEFAULT_SETTINGS,
      loading: false,
      initialized: false,
      formatAmount: (amount) => formatCurrency(amount, DEFAULT_SETTINGS.currency),
      currencySymbol: getCurrencySymbol(DEFAULT_SETTINGS.currency),
      currency: DEFAULT_SETTINGS.currency,
      stockValuationMethod: DEFAULT_SETTINGS.stock_valuation_method,
      pharmacyName: DEFAULT_SETTINGS.pharmacy_name,
      lowStockThreshold: DEFAULT_SETTINGS.low_stock_threshold,
      refreshSettings: () => {},
      updateSettings: async () => false,
    };
  }
  return context;
};

export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const [lastFetchTime, setLastFetchTime] = useState(null);

  // Cache duration in milliseconds (5 minutes)
  const CACHE_DURATION = 5 * 60 * 1000;

  const loadSettings = useCallback(async (forceRefresh = false) => {
    // Vérifier si un token existe
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }

    // Vérifier le cache si pas de force refresh
    if (!forceRefresh && lastFetchTime && (Date.now() - lastFetchTime) < CACHE_DURATION) {
      setLoading(false);
      return;
    }
    
    try {
      const response = await api.get('/settings');
      const newSettings = {
        stock_valuation_method: response.data.stock_valuation_method || 'weighted_average',
        currency: response.data.currency || 'GNF',
        pharmacy_name: response.data.pharmacy_name || '',
        low_stock_threshold: response.data.low_stock_threshold || 10,
      };
      setSettings(newSettings);
      setLastFetchTime(Date.now());
      setInitialized(true);
      
      // Sauvegarder dans localStorage pour persistance
      localStorage.setItem('app_settings', JSON.stringify(newSettings));
    } catch (error) {
      console.error('Error loading settings:', error);
      // Essayer de charger depuis localStorage en cas d'erreur
      const cached = localStorage.getItem('app_settings');
      if (cached) {
        try {
          setSettings(JSON.parse(cached));
          setInitialized(true);
        } catch (e) {
          // Garder les valeurs par défaut
        }
      }
    } finally {
      setLoading(false);
    }
  }, [lastFetchTime, CACHE_DURATION]);

  const updateSettings = useCallback(async (newSettings) => {
    try {
      await api.put('/settings', newSettings);
      setSettings(prev => {
        const updated = { ...prev, ...newSettings };
        localStorage.setItem('app_settings', JSON.stringify(updated));
        return updated;
      });
      setLastFetchTime(Date.now());
      return true;
    } catch (error) {
      console.error('Error updating settings:', error);
      return false;
    }
  }, []);

  const refreshSettings = useCallback(() => {
    loadSettings(true); // Force refresh
  }, [loadSettings]);

  // Fonction utilitaire pour formater les montants avec la devise actuelle - mémoïsée
  const formatAmount = useCallback((amount) => {
    return formatCurrency(amount || 0, settings.currency);
  }, [settings.currency]);

  // Fonction pour obtenir le symbole de la devise actuelle - mémoïsée
  const currencySymbol = useMemo(() => 
    getCurrencySymbol(settings.currency), 
    [settings.currency]
  );

  // Valeurs dérivées mémoïsées
  const derivedValues = useMemo(() => ({
    currency: settings.currency,
    stockValuationMethod: settings.stock_valuation_method,
    pharmacyName: settings.pharmacy_name,
    lowStockThreshold: settings.low_stock_threshold,
  }), [settings]);

  useEffect(() => {
    // Charger les settings au démarrage
    loadSettings();
    
    // Écouter les changements de storage (login/logout)
    const handleStorageChange = (e) => {
      if (e.key === 'token') {
        loadSettings(true);
      }
    };
    window.addEventListener('storage', handleStorageChange);
    
    // Écouter l'événement custom de login
    const handleLogin = () => {
      loadSettings(true);
    };
    window.addEventListener('user-login', handleLogin);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('user-login', handleLogin);
    };
  }, [loadSettings]);

  // Valeur du contexte mémoïsée pour éviter les re-renders inutiles
  const contextValue = useMemo(() => ({
    settings,
    loading,
    initialized,
    updateSettings,
    refreshSettings,
    formatAmount,
    currencySymbol,
    ...derivedValues,
  }), [settings, loading, initialized, updateSettings, refreshSettings, formatAmount, currencySymbol, derivedValues]);

  return (
    <SettingsContext.Provider value={contextValue}>
      {children}
    </SettingsContext.Provider>
  );
};

export default SettingsContext;
