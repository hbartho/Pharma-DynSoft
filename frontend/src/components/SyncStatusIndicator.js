import React from 'react';
import { useOffline } from '../contexts/OfflineContext';
import { Wifi, WifiOff, RefreshCw, Cloud, CloudOff, AlertCircle } from 'lucide-react';
import { Button } from './ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';

const SyncStatusIndicator = ({ compact = false }) => {
  const {
    isOnline,
    isSyncing,
    pendingChangesCount,
    lastSyncTime,
    performSync,
    getTimeSinceLastSync,
  } = useOffline();

  const timeSinceSync = getTimeSinceLastSync();

  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2">
              {isOnline ? (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  {pendingChangesCount > 0 && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">
                      {pendingChangesCount}
                    </span>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-red-500" />
                  <span className="text-xs text-red-600 font-medium">Hors ligne</span>
                </div>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom">
            <div className="text-sm">
              <p className="font-medium">
                {isOnline ? 'Connecté' : 'Hors ligne'}
              </p>
              {pendingChangesCount > 0 && (
                <p className="text-amber-600">
                  {pendingChangesCount} modification(s) en attente
                </p>
              )}
              {timeSinceSync && (
                <p className="text-slate-500">Dernière sync: {timeSinceSync}</p>
              )}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-3">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {isOnline ? (
            <>
              <div className="p-2 bg-emerald-50 rounded-lg">
                <Cloud className="w-5 h-5 text-emerald-600" strokeWidth={1.5} />
              </div>
              <div>
                <p className="font-medium text-slate-900">Connecté</p>
                <p className="text-sm text-slate-500">
                  {timeSinceSync ? `Sync ${timeSinceSync}` : 'Non synchronisé'}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="p-2 bg-amber-50 rounded-lg">
                <CloudOff className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
              </div>
              <div>
                <p className="font-medium text-slate-900">Mode hors ligne</p>
                <p className="text-sm text-amber-600">
                  Les données seront synchronisées au retour en ligne
                </p>
              </div>
            </>
          )}
        </div>

        {isOnline && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => performSync()}
            disabled={isSyncing}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isSyncing ? 'animate-spin' : ''}`} strokeWidth={1.5} />
            {isSyncing ? 'Sync...' : 'Synchroniser'}
          </Button>
        )}
      </div>

      {/* Pending Changes */}
      {pendingChangesCount > 0 && (
        <div className="flex items-center gap-2 p-3 bg-amber-50 rounded-lg border border-amber-100">
          <AlertCircle className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-800">
              {pendingChangesCount} modification{pendingChangesCount > 1 ? 's' : ''} en attente
            </p>
            <p className="text-xs text-amber-600">
              {isOnline
                ? 'Cliquez sur Synchroniser pour envoyer les modifications'
                : 'Sera synchronisé au retour en ligne'}
            </p>
          </div>
        </div>
      )}

      {/* Sync Progress */}
      {isSyncing && (
        <div className="flex items-center gap-2 p-3 bg-teal-50 rounded-lg border border-teal-100">
          <RefreshCw className="w-5 h-5 text-teal-600 animate-spin" strokeWidth={1.5} />
          <p className="text-sm text-teal-700">Synchronisation en cours...</p>
        </div>
      )}
    </div>
  );
};

export default SyncStatusIndicator;
