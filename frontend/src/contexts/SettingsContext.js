import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { formatCurrency, getCurrencySymbol } from '../services/currencyService';

const SettingsContext = createContext();

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    // Retourner des valeurs par défaut si le contexte n'est pas disponible
    return {
      settings: { currency: 'EUR', stock_valuation_method: 'weighted_average' },
      loading: false,
      formatAmount: (amount) => formatCurrency(amount, 'EUR'),
      currencySymbol: '€',
      currency: 'EUR',
      refreshSettings: () => {},
    };
  }
  return context;
};

export const SettingsProvider = ({ children }) => {
  const [settings, setSettings] = useState({
    stock_valuation_method: 'weighted_average',
    currency: 'EUR',
    pharmacy_name: '',
  });
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  const loadSettings = useCallback(async () => {
    // Vérifier si un token existe
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }
    
    try {
      const response = await api.get('/settings');
      setSettings({
        stock_valuation_method: response.data.stock_valuation_method || 'weighted_average',
        currency: response.data.currency || 'EUR',
        pharmacy_name: response.data.pharmacy_name || '',
      });
      setInitialized(true);
    } catch (error) {
      console.error('Error loading settings:', error);
      // Garder les valeurs par défaut en cas d'erreur
    } finally {
      setLoading(false);
    }
  }, []);

  const updateSettings = async (newSettings) => {
    try {
      await api.put('/settings', newSettings);
      setSettings(prev => ({ ...prev, ...newSettings }));
      return true;
    } catch (error) {
      console.error('Error updating settings:', error);
      return false;
    }
  };

  const refreshSettings = useCallback(() => {
    loadSettings();
  }, [loadSettings]);

  // Fonction utilitaire pour formater les montants avec la devise actuelle
  const formatAmount = useCallback((amount) => {
    return formatCurrency(amount || 0, settings.currency);
  }, [settings.currency]);

  // Fonction pour obtenir le symbole de la devise actuelle
  const currencySymbol = getCurrencySymbol(settings.currency);

  useEffect(() => {
    loadSettings();
    
    // Écouter les changements de storage (login/logout)
    const handleStorageChange = () => {
      loadSettings();
    };
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, [loadSettings]);

  return (
    <SettingsContext.Provider value={{
      settings,
      loading,
      initialized,
      updateSettings,
      refreshSettings,
      formatAmount,
      currencySymbol,
      currency: settings.currency,
      stockValuationMethod: settings.stock_valuation_method,
      pharmacyName: settings.pharmacy_name,
    }}>
      {children}
    </SettingsContext.Provider>
  );
};

export default SettingsContext;
