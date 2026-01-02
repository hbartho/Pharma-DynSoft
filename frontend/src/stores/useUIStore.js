/**
 * Zustand Store - État UI Global
 * Gère l'état de l'interface utilisateur (sidebar, modals, notifications, etc.)
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const useUIStore = create(
  persist(
    (set, get) => ({
      // ============================================
      // Sidebar State
      // ============================================
      sidebarCollapsed: false,
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

      // ============================================
      // Theme State
      // ============================================
      theme: 'light', // 'light' | 'dark'
      setTheme: (theme) => set({ theme }),
      toggleTheme: () => set((state) => ({
        theme: state.theme === 'light' ? 'dark' : 'light'
      })),

      // ============================================
      // Modal State
      // ============================================
      activeModal: null, // null | 'createProduct' | 'createSale' | etc.
      modalData: null,
      openModal: (modalName, data = null) => set({ 
        activeModal: modalName, 
        modalData: data 
      }),
      closeModal: () => set({ activeModal: null, modalData: null }),

      // ============================================
      // Notifications State
      // ============================================
      notifications: [],
      addNotification: (notification) => set((state) => ({
        notifications: [
          ...state.notifications,
          {
            id: Date.now(),
            timestamp: new Date().toISOString(),
            read: false,
            ...notification
          }
        ]
      })),
      markNotificationRead: (id) => set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        )
      })),
      clearNotifications: () => set({ notifications: [] }),
      unreadCount: () => get().notifications.filter((n) => !n.read).length,

      // ============================================
      // Loading States
      // ============================================
      globalLoading: false,
      loadingMessage: null,
      setGlobalLoading: (loading, message = null) => set({ 
        globalLoading: loading, 
        loadingMessage: message 
      }),

      // ============================================
      // Table Preferences
      // ============================================
      tablePreferences: {
        products: { pageSize: 10, sortBy: 'name', sortOrder: 'asc' },
        sales: { pageSize: 10, sortBy: 'created_at', sortOrder: 'desc' },
        supplies: { pageSize: 10, sortBy: 'created_at', sortOrder: 'desc' },
        customers: { pageSize: 10, sortBy: 'name', sortOrder: 'asc' },
        suppliers: { pageSize: 10, sortBy: 'name', sortOrder: 'asc' },
      },
      setTablePreference: (table, preference) => set((state) => ({
        tablePreferences: {
          ...state.tablePreferences,
          [table]: { ...state.tablePreferences[table], ...preference }
        }
      })),

      // ============================================
      // Search/Filter States (par page)
      // ============================================
      searchFilters: {
        products: { search: '', category: 'all', stockFilter: 'all' },
        sales: { search: '', dateFrom: null, dateTo: null, agent: '' },
        supplies: { search: '', status: 'all' },
        customers: { search: '' },
        suppliers: { search: '' },
      },
      setSearchFilter: (page, filters) => set((state) => ({
        searchFilters: {
          ...state.searchFilters,
          [page]: { ...state.searchFilters[page], ...filters }
        }
      })),
      clearSearchFilters: (page) => set((state) => ({
        searchFilters: {
          ...state.searchFilters,
          [page]: Object.keys(state.searchFilters[page]).reduce((acc, key) => {
            acc[key] = typeof state.searchFilters[page][key] === 'string' ? '' : null;
            return acc;
          }, {})
        }
      })),

      // ============================================
      // Recent Actions (pour undo/redo potentiel)
      // ============================================
      recentActions: [],
      addRecentAction: (action) => set((state) => ({
        recentActions: [
          { ...action, timestamp: new Date().toISOString() },
          ...state.recentActions.slice(0, 19) // Garder les 20 dernières
        ]
      })),
    }),
    {
      name: 'dynsoft-ui-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Ne persister que certaines valeurs
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        tablePreferences: state.tablePreferences,
      }),
    }
  )
);

export default useUIStore;
