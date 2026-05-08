import React from 'react';
import { useOffline } from '../contexts/OfflineContext';
import { CloudOff, Cloud, RefreshCw, CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from './ui/button';

const SyncStatusIndicator = () => {
  const { 
    isOnline, 
    isSyncing, 
    pendingChangesCount, 
    lastSyncTime,
    performSync 
  } = useOffline();

  const formatLastSync = () => {
    if (!lastSyncTime) return 'Jamais';
    const now = new Date();
    const diff = Math.floor((now - lastSyncTime) / 1000);
    
    if (diff < 60) return 'À l\'instant';
    if (diff < 3600) return `Il y a ${Math.floor(diff / 60)} min`;
    if (diff < 86400) return `Il y a ${Math.floor(diff / 3600)} h`;
    return lastSyncTime.toLocaleDateString('fr-FR');
  };

  // En ligne, pas de changements en attente
  if (isOnline && pendingChangesCount === 0 && !isSyncing) {
    return (
      <div className="flex items-center gap-2 text-emerald-600 text-sm">
        <CheckCircle2 className="w-4 h-4" />
        <span className="hidden sm:inline">Synchronisé</span>
      </div>
    );
  }

  // Synchronisation en cours
  if (isSyncing) {
    return (
      <div className="flex items-center gap-2 text-blue-600 text-sm">
        <RefreshCw className="w-4 h-4 animate-spin" />
        <span className="hidden sm:inline">Synchronisation...</span>
      </div>
    );
  }

  // Hors ligne
  if (!isOnline) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 text-amber-600 text-sm bg-amber-50 px-2 py-1 rounded-full">
          <CloudOff className="w-4 h-4" />
          <span className="hidden sm:inline">Hors ligne</span>
          {pendingChangesCount > 0 && (
            <span className="bg-amber-500 text-white text-xs px-1.5 py-0.5 rounded-full">
              {pendingChangesCount}
            </span>
          )}
        </div>
      </div>
    );
  }

  // En ligne avec changements en attente
  if (pendingChangesCount > 0) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 text-amber-600 text-sm">
          <AlertTriangle className="w-4 h-4" />
          <span className="hidden sm:inline">{pendingChangesCount} en attente</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={performSync}
          className="h-7 px-2 text-teal-600 hover:text-teal-700 hover:bg-teal-50"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>
    );
  }

  return null;
};

export default SyncStatusIndicator;
