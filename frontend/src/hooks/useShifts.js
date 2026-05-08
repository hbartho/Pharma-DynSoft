import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { toast } from 'sonner';

// Récupérer le shift actuel de l'utilisateur
export function useCurrentShift() {
  return useQuery({
    queryKey: ['currentShift'],
    queryFn: async () => {
      const response = await api.get('/shifts/current');
      return response.data;
    },
    staleTime: 30000, // 30 secondes
    refetchOnWindowFocus: true,
  });
}

// Calculer le montant attendu en caisse
export function useExpectedClosing() {
  return useQuery({
    queryKey: ['expectedClosing'],
    queryFn: async () => {
      const response = await api.get('/shifts/calculate-expected');
      return response.data;
    },
    enabled: false, // Ne s'exécute que manuellement
  });
}

// Ouvrir un shift
export function useOpenShift() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/shifts/open', data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['currentShift'], data);
      queryClient.invalidateQueries({ queryKey: ['currentShift'] });
      toast.success('Shift ouvert avec succès', {
        description: `Fond de caisse: ${data.opening_amount?.toLocaleString('fr-FR')} GNF`
      });
    },
    onError: (error) => {
      toast.error('Erreur lors de l\'ouverture du shift', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Clôturer un shift
export function useCloseShift() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/shifts/close', data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['currentShift'], null);
      queryClient.invalidateQueries({ queryKey: ['currentShift'] });
      queryClient.invalidateQueries({ queryKey: ['shiftsHistory'] });
      
      if (data.has_discrepancy) {
        toast.warning('Shift clôturé avec un écart détecté', {
          description: `Écart: ${data.difference?.toLocaleString('fr-FR')} GNF`
        });
      } else {
        toast.success('Shift clôturé avec succès', {
          description: 'Caisse équilibrée'
        });
      }
    },
    onError: (error) => {
      toast.error('Erreur lors de la clôture du shift', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Historique des shifts (admin)
export function useShiftsHistory(filters = {}) {
  const { startDate, endDate, userId } = filters;
  
  return useQuery({
    queryKey: ['shiftsHistory', startDate, endDate, userId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (userId) params.append('user_id', userId);
      
      const response = await api.get(`/shifts/history?${params.toString()}`);
      return response.data;
    },
    staleTime: 60000, // 1 minute
  });
}

// Statistiques des shifts (admin)
export function useShiftsStats() {
  return useQuery({
    queryKey: ['shiftsStats'],
    queryFn: async () => {
      const response = await api.get('/shifts/stats');
      return response.data;
    },
    staleTime: 300000, // 5 minutes
  });
}

// Détails d'un shift spécifique
export function useShiftDetails(shiftId) {
  return useQuery({
    queryKey: ['shift', shiftId],
    queryFn: async () => {
      const response = await api.get(`/shifts/details/${shiftId}`);
      return response.data;
    },
    enabled: !!shiftId,
  });
}

// Marquer une alerte comme affichée
export function useMarkShiftAlert() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (alertType) => {
      const response = await api.patch(`/shifts/mark-alert/${alertType}`);
      return response.data;
    },
    onSuccess: (data, alertType) => {
      // Mettre à jour le cache local du shift
      queryClient.setQueryData(['currentShift'], (oldShift) => {
        if (!oldShift) return oldShift;
        const alertField = {
          '30min': 'alert_30min_shown',
          '5min': 'alert_5min_shown',
          'end': 'alert_end_shown'
        }[alertType];
        return { ...oldShift, [alertField]: true };
      });
    }
  });
}

/**
 * Hook pour vérifier si l'utilisateur peut effectuer des opérations.
 * Les admins sont toujours autorisés, les autres doivent avoir un shift ouvert.
 * 
 * @param {Object} user - L'utilisateur courant (depuis useAuth)
 * @param {Object} currentShift - Le shift courant (depuis useCurrentShift)
 * @returns {Object} { canOperate, reason }
 */
export function useCanOperate(user, currentShift) {
  const isAdmin = user?.role === 'admin';
  const hasOpenShift = !!currentShift;
  
  if (isAdmin) {
    return { 
      canOperate: true, 
      reason: null,
      isAdmin: true 
    };
  }
  
  if (hasOpenShift) {
    return { 
      canOperate: true, 
      reason: null,
      isAdmin: false 
    };
  }
  
  return { 
    canOperate: false, 
    reason: "Vous devez ouvrir un shift de caisse avant de pouvoir effectuer cette opération.",
    isAdmin: false 
  };
}

// Récupérer les shifts actifs (admin)
export function useActiveShifts() {
  return useQuery({
    queryKey: ['activeShifts'],
    queryFn: async () => {
      const response = await api.get('/shifts/active');
      return response.data;
    },
    staleTime: 30000, // 30 secondes
    refetchInterval: 30000, // Rafraîchir toutes les 30 secondes
  });
}

// Prolonger un shift (admin)
export function useExtendShift() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ shiftId, extensionMinutes }) => {
      const response = await api.post(`/shifts/${shiftId}/extend?extension_minutes=${extensionMinutes}`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['activeShifts'] });
      queryClient.invalidateQueries({ queryKey: ['currentShift'] });
      queryClient.invalidateQueries({ queryKey: ['shiftsHistory'] });
      
      toast.success('Shift prolongé avec succès', {
        description: `${data.user_name}: +${data.extension_minutes} minutes`
      });
    },
    onError: (error) => {
      toast.error('Erreur lors de la prolongation', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Supprimer un shift (admin)
export function useDeleteShift() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (shiftId) => {
      const response = await api.delete(`/shifts/${shiftId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shifts'] });
      queryClient.invalidateQueries({ queryKey: ['shiftsHistory'] });
      queryClient.invalidateQueries({ queryKey: ['shiftStats'] });
      
      toast.success('Shift supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}
