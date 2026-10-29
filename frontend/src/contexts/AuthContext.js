import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { toast } from 'sonner';
import { useAutoLogout } from '../hooks/useAutoLogout';
import { getUserData, saveUserData, clearUserData } from '../services/indexedDB';
import { syncData, forceFullSync } from '../services/syncService';
import api from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState(null);

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      const userData = await getUserData();
      if (userData) {
        setUser(userData.user);
        setToken(userData.token);
      }
    } catch (error) {
      console.error('Error loading user data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Synchronisation automatique après connexion
  const performLoginSync = async () => {
    if (!navigator.onLine) {
      console.log('Offline - skipping login sync');
      return { success: false, message: 'Offline' };
    }

    setIsSyncing(true);
    setSyncProgress({ phase: 'starting', message: 'Synchronisation des données...' });

    try {
      // Force une synchronisation complète pour avoir toutes les données
      const result = await forceFullSync();
      
      if (result.success) {
        setSyncProgress({ phase: 'complete', message: `Synchronisation terminée! (${result.pulled} éléments)` });
        console.log('Sync completed:', result);
      } else {
        setSyncProgress({ phase: 'error', message: result.message || 'Erreur de synchronisation' });
      }

      // Effacer le message après un court délai
      setTimeout(() => {
        setSyncProgress(null);
        setIsSyncing(false);
      }, 1500);

      return result;
    } catch (error) {
      console.error('Login sync error:', error);
      setSyncProgress({ phase: 'error', message: 'Erreur de synchronisation' });
      setTimeout(() => {
        setSyncProgress(null);
        setIsSyncing(false);
      }, 2000);
      return { success: false, message: error.message };
    }
  };

  const login = async (email, password) => {
    try {
      const response = await api.post('/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      
      await saveUserData(userData, access_token);
      setUser(userData);
      setToken(access_token);
      sessionStorage.removeItem('adminShiftModalDismissed');
      
      // Déclencher la synchronisation après connexion (en arrière-plan)
      // Ne pas bloquer le login, la sync se fait en parallèle
      setTimeout(() => {
        performLoginSync();
      }, 500);
      
      return { success: true, user: userData };
    } catch (error) {
      return { success: false, status: error.response?.status, message: error.response?.data?.detail || 'Login failed' };
    }
  };

  const register = async (userData) => {
    try {
      await api.post('/auth/register', userData);
      return { success: true };
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || 'Registration failed' };
    }
  };

  const logout = useCallback(async (opts = {}) => {
    await clearUserData();
    sessionStorage.removeItem('adminShiftModalDismissed');
    setUser(null);
    setToken(null);
    setIsSyncing(false);
    setSyncProgress(null);
    if (opts.auto) {
      toast.info('Session fermée automatiquement', { description: `Déconnexion pour ${opts.reason}. Veuillez vous reconnecter.`, duration: 8000 });
    }
  }, []);

  // Déconnexion auto : mise en veille du PC (fermeture d'onglet = session vidée)
  useAutoLogout(!!user, logout);

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isSyncing,
    syncProgress,
    performLoginSync,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};