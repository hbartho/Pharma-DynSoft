import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { toast } from 'sonner';

// Récupérer les planifications avec filtres
export function useShiftSchedules(filters = {}) {
  const { startDate, endDate, userId } = filters;
  
  return useQuery({
    queryKey: ['shift-schedules', startDate, endDate, userId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      if (userId) params.append('user_id', userId);
      
      const response = await api.get(`/shift-schedules?${params.toString()}`);
      return response.data;
    },
    staleTime: 60000, // 1 minute
  });
}

// Vue calendrier mensuelle (admin)
export function useCalendarView(year, month) {
  return useQuery({
    queryKey: ['shift-schedules-calendar', year, month],
    queryFn: async () => {
      const response = await api.get(`/shift-schedules/calendar?year=${year}&month=${month}`);
      return response.data;
    },
    staleTime: 60000,
    enabled: !!year && !!month,
  });
}

// Vue semaine (admin)
export function useWeekView(startDate) {
  return useQuery({
    queryKey: ['shift-schedules-week', startDate],
    queryFn: async () => {
      const response = await api.get(`/shift-schedules/week?start_date=${startDate}`);
      return response.data;
    },
    staleTime: 60000,
    enabled: !!startDate,
  });
}

// Vérifier l'éligibilité de l'utilisateur à ouvrir un shift
export function useShiftEligibility() {
  return useQuery({
    queryKey: ['shift-eligibility'],
    queryFn: async () => {
      const response = await api.get('/shift-schedules/check-eligibility');
      return response.data;
    },
    staleTime: 30000, // 30 secondes
    refetchOnWindowFocus: true,
  });
}

// Récupérer ma planification pour une date
export function useMySchedule(date = null) {
  return useQuery({
    queryKey: ['my-shift-schedule', date],
    queryFn: async () => {
      const params = date ? `?date=${date}` : '';
      const response = await api.get(`/shift-schedules/my-schedule${params}`);
      return response.data;
    },
    staleTime: 60000,
  });
}

// Créer une planification
export function useCreateShiftSchedule() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/shift-schedules', data);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalider TOUTES les requêtes shift-schedules
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && key.startsWith('shift-schedules');
        }
      });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-week'] });
      toast.success('Planification créée', {
        description: `Pour le ${data.schedule?.scheduled_date || 'date'}`
      });
    },
    onError: (error) => {
      toast.error('Erreur lors de la création', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Créer des planifications en masse
export function useCreateBulkSchedules() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/shift-schedules/bulk', data);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalider TOUTES les requêtes shift-schedules
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && key.startsWith('shift-schedules');
        }
      });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-week'] });
      toast.success(data.message, {
        description: data.skipped?.length > 0 
          ? `${data.skipped.length} date(s) ignorée(s) (déjà planifiées)`
          : undefined
      });
    },
    onError: (error) => {
      toast.error('Erreur lors de la création', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Modifier une planification
export function useUpdateShiftSchedule() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ scheduleId, data }) => {
      const response = await api.put(`/shift-schedules/${scheduleId}`, data);
      return response.data;
    },
    onSuccess: () => {
      // Invalider TOUTES les requêtes shift-schedules
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && key.startsWith('shift-schedules');
        }
      });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-week'] });
      toast.success('Planification mise à jour');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Supprimer une planification
export function useDeleteShiftSchedule() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (scheduleId) => {
      const response = await api.delete(`/shift-schedules/${scheduleId}`);
      return response.data;
    },
    onSuccess: () => {
      // Invalider TOUTES les requêtes qui commencent par 'shift-schedules'
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && key.startsWith('shift-schedules');
        }
      });
      // Aussi invalider les requêtes exactes au cas où
      queryClient.invalidateQueries({ queryKey: ['shift-schedules'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-week'] });
      toast.success('Planification supprimée');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}

// Supprimer les planifications d'une date
export function useDeleteSchedulesByDate() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ date, userId }) => {
      const params = userId ? `?user_id=${userId}` : '';
      const response = await api.delete(`/shift-schedules/date/${date}${params}`);
      return response.data;
    },
    onSuccess: (data) => {
      // Invalider TOUTES les requêtes shift-schedules
      queryClient.invalidateQueries({ 
        predicate: (query) => {
          const key = query.queryKey[0];
          return typeof key === 'string' && key.startsWith('shift-schedules');
        }
      });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-calendar'] });
      queryClient.invalidateQueries({ queryKey: ['shift-schedules-week'] });
      toast.success(data.message);
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression', {
        description: error.response?.data?.detail || 'Une erreur est survenue'
      });
    }
  });
}
