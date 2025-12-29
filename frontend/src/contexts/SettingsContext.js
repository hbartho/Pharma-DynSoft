import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';
import { formatCurrency, getCurrencySymbol } from '../services/currencyService';

const SettingsContext = createContext();

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettings must be used within a SettingsProvider');
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

  const loadSettings = async () => {
    try {
      const response = await api.get('/settings');
      setSettings({
        stock_valuation_method: response.data.stock_valuation_method || 'weighted_average',
        currency: response.data.currency || 'EUR',
        pharmacy_name: response.data.pharmacy_name || '',
      });
    } catch (error) {
      console.error('Error loading settings:', error);
      // Garder les valeurs par défaut en cas d'erreur
    } finally {
      setLoading(false);
    }
  };

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

  const refreshSettings = () => {
    loadSettings();
  };

  // Fonction utilitaire pour formater les montants avec la devise actuelle
  const formatAmount = (amount) => {
    return formatCurrency(amount, settings.currency);
  };

  // Fonction pour obtenir le symbole de la devise actuelle
  const currencySymbol = getCurrencySymbol(settings.currency);

  useEffect(() => {
    loadSettings();
  }, []);

  return (
    <SettingsContext.Provider value={{
      settings,
      loading,
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
