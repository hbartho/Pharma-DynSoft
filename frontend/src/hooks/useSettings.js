/**
 * React Query Hooks - Paramètres
 * Hooks pour la gestion des paramètres avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer les paramètres
 */
export const useSettingsQuery = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.settings,
    queryFn: async () => {
      const response = await api.get('/settings');
      return response.data;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes (les paramètres changent rarement)
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Mettre à jour les paramètres
 */
export const useUpdateSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (settingsData) => {
      const response = await api.put('/settings', settingsData);
      return response.data;
    },
    onSuccess: (updatedSettings) => {
      queryClient.setQueryData(queryKeys.settings, updatedSettings);
      toast.success('Paramètres enregistrés avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de l\'enregistrement des paramètres', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Obtenir une valeur de paramètre spécifique
 */
export const useSettingValue = (key, defaultValue = null) => {
  const { data: settings } = useSettingsQuery();
  return settings?.[key] ?? defaultValue;
};

/**
 * Obtenir la devise configurée
 */
export const useCurrency = () => {
  return useSettingValue('currency', 'GNF');
};

/**
 * Obtenir le seuil de stock bas
 */
export const useLowStockThreshold = () => {
  return useSettingValue('low_stock_threshold', 10);
};

/**
 * Obtenir le délai de retour
 */
export const useReturnDelayDays = () => {
  return useSettingValue('return_delay_days', 3);
};

/**
 * Obtenir le délai d'alerte de péremption
 */
export const useExpirationAlertDays = () => {
  return useSettingValue('expiration_alert_days', 30);
};

/**
 * Obtenir le nom de la pharmacie
 */
export const usePharmacyName = () => {
  return useSettingValue('pharmacy_name', 'DynSoft Pharma');
};

export default {
  useSettingsQuery,
  useUpdateSettings,
  useSettingValue,
  useCurrency,
  useLowStockThreshold,
  useReturnDelayDays,
  useExpirationAlertDays,
  usePharmacyName,
};
