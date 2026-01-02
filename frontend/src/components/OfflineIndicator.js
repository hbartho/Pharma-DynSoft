/**
 * Composant indicateur de statut online/offline
 * Affiche l'état de connexion et les opérations en attente
 */

import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff, Cloud, CloudOff, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import { useOffline } from '../contexts/OfflineContext';
import { Button } from './ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';

const OfflineIndicator = ({ className, showDetails = false }) => {
  const {
    isOnline,
    isSyncing,
    pendingChangesCount,
    lastSyncTime,
    syncProgress,
    performSync,
    getTimeSinceLastSync
  } = useOffline();

  const [showTooltip, setShowTooltip] = useState(false);

  // Déterminer l'état et les couleurs
  const getStatus = () => {
    if (!isOnline) {
      return {
        icon: WifiOff,
        color: 'text-red-500',
        bgColor: 'bg-red-100',
        borderColor: 'border-red-200',
        label: 'Hors ligne',
        description: 'Les modifications seront synchronisées automatiquement'
      };
    }
    
    if (isSyncing) {
      return {
        icon: RefreshCw,
        color: 'text-blue-500',
        bgColor: 'bg-blue-100',
        borderColor: 'border-blue-200',
        label: 'Synchronisation...',
        description: syncProgress?.message || 'En cours...'
      };
    }
    
    if (pendingChangesCount > 0) {
      return {
        icon: CloudOff,
        color: 'text-amber-500',
        bgColor: 'bg-amber-100',
        borderColor: 'border-amber-200',
        label: `${pendingChangesCount} en attente`,
        description: 'Des modifications doivent être synchronisées'
      };
    }
    
    return {
      icon: Cloud,
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-100',
      borderColor: 'border-emerald-200',
      label: 'Synchronisé',
      description: lastSyncTime ? `Dernière sync: ${getTimeSinceLastSync()}` : 'Tout est à jour'
    };
  };

  const status = getStatus();
  const StatusIcon = status.icon;

  // Version compacte (pour la sidebar)
  if (!showDetails) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className={cn(
                'flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all',
                status.bgColor,
                status.borderColor,
                'border',
                className
              )}
              onClick={() => isOnline && pendingChangesCount > 0 && performSync()}
            >
              <StatusIcon 
                className={cn(
                  'w-4 h-4',
                  status.color,
                  isSyncing && 'animate-spin'
                )} 
              />
              <span className={cn('text-sm font-medium', status.color)}>
                {status.label}
              </span>
              {pendingChangesCount > 0 && (
                <Badge variant="secondary" className="ml-auto">
                  {pendingChangesCount}
                </Badge>
              )}
            </div>
          </TooltipTrigger>
          <TooltipContent side="right">
            <p>{status.description}</p>
            {isOnline && pendingChangesCount > 0 && (
              <p className="text-xs text-slate-400 mt-1">Cliquez pour synchroniser</p>
            )}
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  // Version détaillée (pour les paramètres ou modal)
  return (
    <div className={cn(
      'rounded-xl border p-4',
      status.bgColor,
      status.borderColor,
      className
    )}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={cn(
            'p-2 rounded-lg',
            isOnline ? 'bg-emerald-200' : 'bg-red-200'
          )}>
            {isOnline ? (
              <Wifi className="w-5 h-5 text-emerald-600" />
            ) : (
              <WifiOff className="w-5 h-5 text-red-600" />
            )}
          </div>
          <div>
            <h4 className="font-semibold text-slate-800">
              {isOnline ? 'Connecté' : 'Mode hors ligne'}
            </h4>
            <p className="text-sm text-slate-600">
              {status.description}
            </p>
          </div>
        </div>
        
        {isOnline && (
          <Button
            variant="outline"
            size="sm"
            onClick={performSync}
            disabled={isSyncing}
            className="gap-2"
          >
            <RefreshCw className={cn('w-4 h-4', isSyncing && 'animate-spin')} />
            Synchroniser
          </Button>
        )}
      </div>

      {/* Détails de synchronisation */}
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div className="text-center p-3 bg-white/50 rounded-lg">
          <div className="text-2xl font-bold text-slate-800">
            {pendingChangesCount}
          </div>
          <div className="text-xs text-slate-500">En attente</div>
        </div>
        <div className="text-center p-3 bg-white/50 rounded-lg">
          <div className="text-2xl font-bold text-slate-800">
            {lastSyncTime ? getTimeSinceLastSync() : '-'}
          </div>
          <div className="text-xs text-slate-500">Dernière sync</div>
        </div>
        <div className="text-center p-3 bg-white/50 rounded-lg">
          <div className="flex justify-center">
            {isOnline ? (
              <CheckCircle className="w-6 h-6 text-emerald-500" />
            ) : (
              <AlertCircle className="w-6 h-6 text-amber-500" />
            )}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {isOnline ? 'En ligne' : 'Hors ligne'}
          </div>
        </div>
      </div>

      {/* Barre de progression pendant la sync */}
      {isSyncing && syncProgress && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-slate-600 mb-1">
            <span>{syncProgress.message}</span>
            {syncProgress.current && syncProgress.total && (
              <span>{syncProgress.current}/{syncProgress.total}</span>
            )}
          </div>
          <div className="h-2 bg-white/50 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ 
                width: syncProgress.total 
                  ? `${(syncProgress.current / syncProgress.total) * 100}%` 
                  : '50%' 
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};

// Badge minimaliste pour la barre de navigation
export const OfflineBadge = ({ className }) => {
  const { isOnline, pendingChangesCount, isSyncing } = useOffline();

  if (isOnline && pendingChangesCount === 0 && !isSyncing) {
    return null;
  }

  return (
    <div className={cn(
      'flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
      !isOnline ? 'bg-red-100 text-red-700' : 
      isSyncing ? 'bg-blue-100 text-blue-700' :
      'bg-amber-100 text-amber-700',
      className
    )}>
      {!isOnline ? (
        <>
          <WifiOff className="w-3 h-3" />
          <span>Hors ligne</span>
        </>
      ) : isSyncing ? (
        <>
          <RefreshCw className="w-3 h-3 animate-spin" />
          <span>Sync...</span>
        </>
      ) : (
        <>
          <CloudOff className="w-3 h-3" />
          <span>{pendingChangesCount}</span>
        </>
      )}
    </div>
  );
};

export default OfflineIndicator;
