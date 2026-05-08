/**
 * Zustand Store - État d'authentification
 * Gère l'utilisateur connecté et les tokens
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const useAuthStore = create(
  persist(
    (set, get) => ({
      // ============================================
      // User State
      // ============================================
      user: null,
      token: null,
      isAuthenticated: false,

      // ============================================
      // Actions
      // ============================================
      setUser: (user, token) => set({
        user,
        token,
        isAuthenticated: !!user && !!token,
      }),

      updateUser: (updates) => set((state) => ({
        user: state.user ? { ...state.user, ...updates } : null,
      })),

      logout: () => set({
        user: null,
        token: null,
        isAuthenticated: false,
      }),

      // ============================================
      // Getters
      // ============================================
      getToken: () => get().token,
      getUser: () => get().user,
      getUserRole: () => get().user?.role || null,
      getEmployeeCode: () => get().user?.employee_code || null,
      getTenantId: () => get().user?.tenant_id || null,

      // ============================================
      // Role Checks
      // ============================================
      isAdmin: () => get().user?.role === 'admin',
      isPharmacien: () => get().user?.role === 'pharmacien',
      isCaissier: () => get().user?.role === 'caissier',
      hasRole: (roles) => {
        const userRole = get().user?.role;
        if (!userRole) return false;
        return Array.isArray(roles) ? roles.includes(userRole) : roles === userRole;
      },

      // ============================================
      // Permissions
      // ============================================
      canAccessProducts: () => get().hasRole(['admin', 'pharmacien']),
      canAccessSettings: () => get().hasRole(['admin']),
      canAccessUsers: () => get().hasRole(['admin']),
      canValidateSupplies: () => get().hasRole(['admin']),
      canCreateSales: () => get().hasRole(['admin', 'pharmacien', 'caissier']),
    }),
    {
      name: 'dynsoft-auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
