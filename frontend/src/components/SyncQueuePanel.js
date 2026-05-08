/**
 * Composant de Queue de Synchronisation
 * Affiche les opérations en attente et permet de les gérer
 */

import React, { useState, useEffect } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  Cloud, 
  CloudOff, 
  RefreshCw, 
  Trash2, 
  AlertTriangle,
  Check,
  Clock,
  ChevronDown,
  ChevronUp,
  Package,
  Users,
  Truck,
  ShoppingCart,
  RotateCcw,
  X
} from 'lucide-react';
import { useOffline } from '../contexts/OfflineContext';
import { getLocalChanges, clearLocalChanges, updateChangeStatus } from '../services/indexedDB';
import { syncAllPendingOperations } from '../services/offlineService';
import { toast } from 'sonner';

const ENTITY_ICONS = {
  products: Package,
  customers: Users,
  suppliers: Truck,
  sales: ShoppingCart,
  returns: RotateCcw,
  categories: Package,
  units: Package,
  supplies: Truck,
  prescriptions: Package,
};

const ACTION_LABELS = {
  create: 'Créer',
  update: 'Modifier',
  delete: 'Supprimer',
};

const STATUS_COLORS = {
  pending: 'bg-amber-100 text-amber-800',
  syncing: 'bg-blue-100 text-blue-800',
  synced: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
};

const SyncQueuePanel = ({ className = '' }) => {
  const { isOnline, isSyncing, performSync, pendingChangesCount, lastSyncTime, getTimeSinceLastSync } = useOffline();
  const [expanded, setExpanded] = useState(false);
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(false);

  // Charger les changements en attente
  const loadChanges = async () => {
    try {
      const allChanges = await getLocalChanges();
      setChanges(allChanges.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)));
    } catch (error) {
      console.error('Error loading changes:', error);
    }
  };

  useEffect(() => {
    loadChanges();
    
    // Rafraîchir toutes les 10 secondes
    const interval = setInterval(loadChanges, 10000);
    return () => clearInterval(interval);
  }, []);

  // Synchroniser maintenant
  const handleSync = async () => {
    if (!isOnline) {
      toast.error('Synchronisation impossible en mode hors-ligne');
      return;
    }

    setLoading(true);
    try {
      await performSync();
      await loadChanges();
    } catch (error) {
      toast.error('Erreur de synchronisation');
    } finally {
      setLoading(false);
    }
  };

  // Supprimer tous les changements en attente
  const handleClearAll = async () => {
    if (window.confirm('Supprimer toutes les modifications en attente ? Cette action est irréversible.')) {
      try {
        await clearLocalChanges();
        setChanges([]);
        toast.success('Modifications supprimées');
      } catch (error) {
        toast.error('Erreur lors de la suppression');
      }
    }
  };

  // Réessayer un changement en erreur
  const handleRetry = async (change) => {
    if (!isOnline) {
      toast.error('Impossible de synchroniser hors-ligne');
      return;
    }

    try {
      await updateChangeStatus(change.id, 'pending');
      await loadChanges();
      toast.info('Réessai programmé');
    } catch (error) {
      toast.error('Erreur');
    }
  };

  const pendingCount = changes.filter(c => c.status === 'pending').length;
  const errorCount = changes.filter(c => c.status === 'error').length;
  const syncedCount = changes.filter(c => c.status === 'synced').length;

  // Ne pas afficher si tout est synchronisé et en ligne
  if (isOnline && changes.length === 0) {
    return null;
  }

  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>
      {/* Header */}
      <div 
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {isOnline ? (
            <Cloud className="w-5 h-5 text-emerald-600" />
          ) : (
            <CloudOff className="w-5 h-5 text-red-500" />
          )}
          
          <div>
            <h3 className="font-medium text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              File de synchronisation
            </h3>
            <p className="text-sm text-slate-500">
              {isOnline ? (
                lastSyncTime ? `Dernière sync: ${getTimeSinceLastSync()}` : 'Jamais synchronisé'
              ) : (
                'Mode hors-ligne'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {pendingCount > 0 && (
            <Badge className="bg-amber-100 text-amber-800">
              <Clock className="w-3 h-3 mr-1" />
              {pendingCount} en attente
            </Badge>
          )}
          {errorCount > 0 && (
            <Badge className="bg-red-100 text-red-800">
              <AlertTriangle className="w-3 h-3 mr-1" />
              {errorCount} erreur{errorCount > 1 ? 's' : ''}
            </Badge>
          )}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </div>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-slate-100">
          {/* Actions */}
          <div className="flex items-center gap-2 p-4 bg-slate-50">
            <Button
              size="sm"
              onClick={handleSync}
              disabled={!isOnline || isSyncing || loading || pendingCount === 0}
              className="bg-teal-600 hover:bg-teal-700"
            >
              <RefreshCw className={`w-4 h-4 mr-1 ${(isSyncing || loading) ? 'animate-spin' : ''}`} />
              {isSyncing ? 'Synchronisation...' : 'Synchroniser'}
            </Button>
            
            {changes.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleClearAll}
                className="text-red-600 hover:bg-red-50"
              >
                <Trash2 className="w-4 h-4 mr-1" />
                Tout supprimer
              </Button>
            )}
          </div>

          {/* Liste des changements */}
          <div className="max-h-64 overflow-y-auto">
            {changes.length === 0 ? (
              <div className="p-6 text-center text-slate-500">
                <Check className="w-8 h-8 mx-auto mb-2 text-emerald-500" />
                <p>Tout est synchronisé</p>
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {changes.slice(0, 20).map((change) => {
                  const Icon = ENTITY_ICONS[change.type] || Package;
                  const isError = change.status === 'error';
                  const isPending = change.status === 'pending';
                  
                  return (
                    <div
                      key={change.id}
                      className={`flex items-center justify-between p-3 ${isError ? 'bg-red-50' : ''}`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-1.5 rounded ${isError ? 'bg-red-100' : 'bg-slate-100'}`}>
                          <Icon className={`w-4 h-4 ${isError ? 'text-red-600' : 'text-slate-600'}`} />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">
                            {ACTION_LABELS[change.action]} {change.type}
                          </p>
                          <p className="text-xs text-slate-500">
                            {new Date(change.timestamp).toLocaleString('fr-FR')}
                          </p>
                          {change.lastError && (
                            <p className="text-xs text-red-600 mt-1">
                              {change.lastError}
                            </p>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <Badge className={STATUS_COLORS[change.status]}>
                          {change.status === 'pending' && <Clock className="w-3 h-3 mr-1" />}
                          {change.status === 'syncing' && <RefreshCw className="w-3 h-3 mr-1 animate-spin" />}
                          {change.status === 'synced' && <Check className="w-3 h-3 mr-1" />}
                          {change.status === 'error' && <AlertTriangle className="w-3 h-3 mr-1" />}
                          {change.status}
                        </Badge>
                        
                        {isError && isOnline && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleRetry(change)}
                            className="h-7 px-2"
                          >
                            <RefreshCw className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer avec stats */}
          {changes.length > 0 && (
            <div className="flex items-center justify-between p-3 bg-slate-50 border-t border-slate-100 text-xs text-slate-500">
              <span>{changes.length} opération{changes.length > 1 ? 's' : ''} au total</span>
              {changes.length > 20 && <span>+ {changes.length - 20} autres</span>}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SyncQueuePanel;
