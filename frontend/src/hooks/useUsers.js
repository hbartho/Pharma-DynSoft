/**
 * React Query Hooks - Utilisateurs
 * Hooks pour la gestion des utilisateurs avec cache intelligent
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { queryKeys } from '../lib/queryClient';
import { toast } from 'sonner';

// ============================================
// Queries
// ============================================

/**
 * Récupérer tous les utilisateurs
 */
export const useUsers = (options = {}) => {
  return useQuery({
    queryKey: queryKeys.users,
    queryFn: async () => {
      const response = await api.get('/users');
      return response.data;
    },
    staleTime: 5 * 60 * 1000,
    ...options,
  });
};

/**
 * Récupérer un utilisateur par ID
 */
export const useUser = (userId, options = {}) => {
  return useQuery({
    queryKey: queryKeys.user(userId),
    queryFn: async () => {
      const response = await api.get(`/users/${userId}`);
      return response.data;
    },
    enabled: !!userId,
    ...options,
  });
};

// ============================================
// Mutations
// ============================================

/**
 * Créer un utilisateur
 */
export const useCreateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userData) => {
      const response = await api.post('/users', userData);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users });
      toast.success('Utilisateur créé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la création de l\'utilisateur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Mettre à jour un utilisateur
 */
export const useUpdateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ userId, data }) => {
      const response = await api.put(`/users/${userId}`, data);
      return response.data;
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(queryKeys.user(updatedUser.id), updatedUser);
      queryClient.invalidateQueries({ queryKey: queryKeys.users });
      toast.success('Utilisateur mis à jour avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la mise à jour de l\'utilisateur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Supprimer un utilisateur
 */
export const useDeleteUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId) => {
      await api.delete(`/users/${userId}`);
      return userId;
    },
    onSuccess: (userId) => {
      queryClient.removeQueries({ queryKey: queryKeys.user(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users });
      toast.success('Utilisateur supprimé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la suppression de l\'utilisateur', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Activer/Désactiver un utilisateur
 */
export const useToggleUserStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (userId) => {
      const response = await api.patch(`/users/${userId}/toggle-status`);
      return response.data;
    },
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(queryKeys.user(updatedUser.id), updatedUser);
      queryClient.invalidateQueries({ queryKey: queryKeys.users });
      toast.success(
        updatedUser.is_active 
          ? 'Utilisateur activé' 
          : 'Utilisateur désactivé'
      );
    },
    onError: (error) => {
      toast.error('Erreur lors du changement de statut', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

/**
 * Réinitialiser le mot de passe
 */
export const useResetUserPassword = () => {
  return useMutation({
    mutationFn: async ({ userId, newPassword }) => {
      const response = await api.put(
        `/users/${userId}/password?new_password=${encodeURIComponent(newPassword)}`
      );
      return response.data;
    },
    onSuccess: () => {
      toast.success('Mot de passe réinitialisé avec succès');
    },
    onError: (error) => {
      toast.error('Erreur lors de la réinitialisation du mot de passe', {
        description: error.response?.data?.detail || error.message,
      });
    },
  });
};

// ============================================
// Hooks utilitaires
// ============================================

/**
 * Rechercher des utilisateurs
 */
export const useUserSearch = (searchTerm = '') => {
  const { data: users = [], ...rest } = useUsers();

  const filteredUsers = users.filter((user) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      user.name?.toLowerCase().includes(term) ||
      user.email?.toLowerCase().includes(term) ||
      user.employee_code?.toLowerCase().includes(term)
    );
  });

  return { data: filteredUsers, ...rest };
};

/**
 * Filtrer par rôle
 */
export const useUsersByRole = (role) => {
  const { data: users = [], ...rest } = useUsers();
  const filteredUsers = role 
    ? users.filter(u => u.role === role)
    : users;
  return { data: filteredUsers, ...rest };
};

export default {
  useUsers,
  useUser,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useToggleUserStatus,
  useResetUserPassword,
  useUserSearch,
  useUsersByRole,
};
