/**
 * React Query Hooks - Ordonnances
 * Hooks pour la gestion des ordonnances avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// Ajout de queryKey pour prescriptions dans le fichier
const prescriptionKeys = {
  prescriptions: ['prescriptions'],
  prescription: (id) => ['prescriptions', id],
};

// ============================================
// Queries
// ============================================

/**
 * Récupérer toutes les ordonnances
 */
export const usePrescriptions = (options = {}) => {
  return useQuery({
    queryKey: prescriptionKeys.prescriptions,
    queryFn: async () => {
      const response = await api.get('/prescriptions');
      return response.data;
    },
    staleTime: 2 * 60 * 1000,
    ...options,
  });
};

/**
 * Récupérer une ordonnance par ID
 */
export const usePrescription = (prescriptionId, options = {}) => {
  return useQuery({
    queryKey: prescriptionKeys.prescription(prescriptionId),
    queryFn: async () => {
      const response = await api.get(`/prescriptions/${prescriptionId}`);
      return response.data;
    },
    enabled: !!prescriptionId,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer une ordonnance
 */
export const useCreatePrescription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (prescriptionData) => {
      const response = await api.post('/prescriptions', prescriptionData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.prescriptions });
      toast.success('Ordonnance créée avec succès');
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la création de l\'ordonnance', {
        description: errorMessage,
      });
    },
  });
};

/**
 * Mettre à jour une ordonnance
 */
export const useUpdatePrescription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ prescriptionId, data }) => {
      const response = await api.put(`/prescriptions/${prescriptionId}/edit`, data);
      return response.data;
    },
    onSuccess: (updatedPrescription) => {
      queryClient.setQueryData(
        prescriptionKeys.prescription(updatedPrescription.id), 
        updatedPrescription
      );
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.prescriptions });
      toast.success('Ordonnance mise à jour avec succès');
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la mise à jour de l\'ordonnance', {
        description: errorMessage,
      });
    },
  });
};

/**
 * Supprimer une ordonnance
 */
export const useDeletePrescription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (prescriptionId) => {
      await api.delete(`/prescriptions/${prescriptionId}`);
      return prescriptionId;
    },
    onSuccess: (prescriptionId) => {
      queryClient.removeQueries({ queryKey: prescriptionKeys.prescription(prescriptionId) });
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.prescriptions });
      toast.success('Ordonnance supprimée avec succès');
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la suppression de l\'ordonnance', {
        description: errorMessage,
      });
    },
  });
};

/**
 * Marquer une ordonnance comme dispensée
 */
export const useFulfillPrescription = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (prescriptionId) => {
      const response = await api.put(`/prescriptions/${prescriptionId}/status?new_status=fulfilled`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prescriptionKeys.prescriptions });
      toast.success('Ordonnance marquée comme dispensée');
    },
    onError: (error) => {
      const detail = error.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail?.msg || error.message || 'Erreur inconnue');
      toast.error('Erreur lors de la mise à jour du statut', {
        description: errorMessage,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Filtrer par statut
 */
export const usePrescriptionsByStatus = (status) => {
  const { data: prescriptions = [], ...rest } = usePrescriptions();
  const filtered = status 
    ? prescriptions.filter(p => p.status === status)
    : prescriptions;
  return { data: filtered, ...rest };
};

/**
 * Ordonnances en attente
 */
export const usePendingPrescriptions = () => {
  return usePrescriptionsByStatus('pending');
};

/**
 * Rechercher des ordonnances
 */
export const usePrescriptionSearch = (searchTerm = '', customerId = null) => {
  const { data: prescriptions = [], ...rest } = usePrescriptions();

  const filtered = prescriptions.filter((prescription) => {
    const matchesSearch = !searchTerm || 
      prescription.patient_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prescription.doctor_name?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCustomer = !customerId || prescription.customer_id === customerId;

    return matchesSearch && matchesCustomer;
  });

  return { data: filtered, ...rest };
};

/**
 * Récupérer les statistiques des ordonnances
 */
export const usePrescriptionStats = (options = {}) => {
  return useQuery({
    queryKey: ['prescriptions', 'stats'],
    queryFn: async () => {
      const response = await api.get('/prescriptions/stats');
      return response.data;
    },
    staleTime: 30 * 1000, // 30 secondes
    ...options,
  });
};

export default {
  usePrescriptions,
  usePrescription,
  useCreatePrescription,
  useUpdatePrescription,
  useDeletePrescription,
  useFulfillPrescription,
  usePrescriptionsByStatus,
  usePendingPrescriptions,
  usePrescriptionSearch,
  usePrescriptionStats,
};
