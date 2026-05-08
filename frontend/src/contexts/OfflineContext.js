import React, { createContext, useState, useContext, useEffect, useCallback, useRef } from 'react';
import { 
  syncData, 
  startAutoSync, 
  stopAutoSync, 
  getSyncStatus,
  addSyncListener,
  forceFullSync as forceFullSyncService
} from '../services/syncService';
import { 
  getLastSyncTime, 
  getPendingChanges,
  getStoreCounts 
} from '../services/indexedDB';
import { toast } from 'sonner';

const OfflineContext = createContext();

export const useOffline = () => {
  const context = useContext(OfflineContext);
  if (!context) {
    throw new Error('useOffline must be used within OfflineProvider');
  }
  return context;
};

export const OfflineProvider = ({ children }) => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState(null);
  const [syncProgress, setSyncProgress] = useState(null);
  const [pendingChangesCount, setPendingChangesCount] = useState(0);
  const [syncStats, setSyncStats] = useState(null);
  const autoSyncStarted = useRef(false);

  // Initialize sync status
  const refreshSyncStatus = useCallback(async () => {
    try {
      const status = await getSyncStatus();
      setLastSyncTime(status.lastSyncTime ? new Date(status.lastSyncTime) : null);
      setPendingChangesCount(status.pendingChanges);
      setSyncStats(status.storeCounts);
    } catch (error) {
      console.error('Error getting sync status:', error);
    }
  }, []);

  // Handle online/offline events
  useEffect(() => {
    const handleOnline = async () => {
      setIsOnline(true);
      toast.success('Connexion rétablie', {
        description: 'Synchronisation en cours...'
      });
      // Sync when coming back online
      await performSync();
    };

    const handleOffline = () => {
      setIsOnline(false);
      toast.warning('Mode hors ligne', {
        description: 'Les modifications seront synchronisées ultérieurement'
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Listen to sync events
  useEffect(() => {
    const unsubscribe = addSyncListener((event) => {
      switch (event.type) {
        case 'sync_start':
          setIsSyncing(true);
          setSyncProgress({ phase: 'starting', message: 'Démarrage de la synchronisation...' });
          break;
          
        case 'push_start':
          setSyncProgress({ phase: 'push', message: 'Envoi des modifications locales...' });
          break;
          
        case 'push_progress':
          setSyncProgress({ 
            phase: 'push', 
            current: event.current, 
            total: event.total,
            message: `Envoi ${event.current}/${event.total}...`
          });
          break;
          
        case 'push_complete':
          if (event.results.pushed > 0) {
            console.log(`Pushed ${event.results.pushed} changes`);
          }
          break;
          
        case 'pull_start':
          setSyncProgress({ phase: 'pull', message: 'Récupération des données...' });
          break;
          
        case 'pull_progress':
          setSyncProgress({ 
            phase: 'pull', 
            current: event.current, 
            total: event.total,
            store: event.store,
            message: `Synchronisation ${event.store}...`
          });
          break;
          
        case 'pull_complete':
          console.log(`Pulled ${event.results.totalPulled} items`);
          break;
          
        case 'sync_complete':
          setIsSyncing(false);
          setSyncProgress(null);
          setLastSyncTime(new Date(event.timestamp));
          refreshSyncStatus();
          break;
          
        case 'sync_error':
          setIsSyncing(false);
          setSyncProgress(null);
          console.error('Sync error:', event.error);
          break;
          
        default:
          break;
      }
    });

    return () => unsubscribe();
  }, [refreshSyncStatus]);

  // Start auto sync when online and authenticated
  useEffect(() => {
    const initAutoSync = async () => {
      if (!autoSyncStarted.current && isOnline) {
        autoSyncStarted.current = true;
        startAutoSync();
        await refreshSyncStatus();
      }
    };

    initAutoSync();

    return () => {
      stopAutoSync();
    };
  }, [isOnline, refreshSyncStatus]);

  // Perform manual sync
  const performSync = useCallback(async (options = {}) => {
    if (!isOnline) {
      toast.error('Synchronisation impossible', {
        description: 'Vous êtes hors ligne'
      });
      return { success: false };
    }

    if (isSyncing) {
      toast.info('Synchronisation déjà en cours');
      return { success: false };
    }

    try {
      const result = await syncData(options);
      
      if (result.success) {
        const message = result.pushed > 0 || result.pulled > 0
          ? `${result.pushed} envoyé(s), ${result.pulled} reçu(s)`
          : 'Tout est à jour';
          
        toast.success('Synchronisation terminée', {
          description: message
        });
      } else {
        toast.error('Erreur de synchronisation', {
          description: result.message
        });
      }
      
      return result;
    } catch (error) {
      toast.error('Erreur de synchronisation', {
        description: error.message
      });
      return { success: false, error };
    }
  }, [isOnline, isSyncing]);

  // Force full sync (re-download all data)
  const forceFullSync = useCallback(async () => {
    if (!isOnline) {
      toast.error('Synchronisation impossible', {
        description: 'Vous êtes hors ligne'
      });
      return { success: false };
    }

    toast.info('Synchronisation complète en cours...');
    
    try {
      const result = await forceFullSyncService();
      
      if (result.success) {
        toast.success('Synchronisation complète terminée', {
          description: `${result.pulled} éléments synchronisés`
        });
      }
      
      return result;
    } catch (error) {
      toast.error('Erreur de synchronisation');
      return { success: false, error };
    }
  }, [isOnline]);

  // Get time since last sync
  const getTimeSinceLastSync = useCallback(() => {
    if (!lastSyncTime) return null;
    
    const now = new Date();
    const diff = now - lastSyncTime;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
      return `il y a ${hours}h ${minutes % 60}min`;
    } else if (minutes > 0) {
      return `il y a ${minutes} min`;
    } else {
      return 'à l\'instant';
    }
  }, [lastSyncTime]);

  const value = {
    // State
    isOnline,
    isSyncing,
    lastSyncTime,
    syncProgress,
    pendingChangesCount,
    syncStats,
    
    // Actions
    performSync,
    forceFullSync,
    refreshSyncStatus,
    
    // Helpers
    getTimeSinceLastSync,
  };

  return (
    <OfflineContext.Provider value={value}>
      {children}
    </OfflineContext.Provider>
  );
};

export default OfflineContext;
