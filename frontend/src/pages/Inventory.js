import React, { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Package, ClipboardList, Search, CheckCircle2, XCircle, AlertTriangle,
  Plus, Minus, BarChart3, FileCheck, History, Loader2, Filter, ArrowUpDown,
  TrendingUp, TrendingDown, CheckCheck, X, RefreshCw, Printer, Eye, Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';
import { useCategories } from '../hooks/useCategories';

// Hook pour l'inventaire avec rafraîchissement intelligent
const useCurrentInventory = (options = {}) => {
  const { enableAutoRefresh = false } = options;
  
  return useQuery({
    queryKey: ['inventory', 'current'],
    queryFn: async () => {
      const response = await api.get('/inventory/sessions/active');
      return response.data;
    },
    staleTime: 10000, // Cache pendant 10 secondes
    // Rafraîchissement uniquement si activé ET inventaire en cours
    refetchInterval: enableAutoRefresh ? 15000 : false, // 15 secondes si activé
    refetchIntervalInBackground: false, // Ne pas rafraîchir en arrière-plan
  });
};

const useInventoryHistory = (year = null) => {
  return useInfiniteQuery({
    queryKey: ['inventory', 'history', year],
    queryFn: async ({ pageParam = 0 }) => {
      const params = new URLSearchParams();
      params.append('skip', pageParam);
      params.append('limit', '10');
      if (year) params.append('year', year);
      
      const response = await api.get(`/inventory/sessions/history?${params.toString()}`);
      return response.data;
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.has_more) {
        return lastPage.skip + lastPage.limit;
      }
      return undefined;
    },
    initialPageParam: 0,
  });
};

const useCreateInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const response = await api.post('/inventory/sessions', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inventory']);
      toast.success('Session d\'inventaire créée');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la création');
    },
  });
};

const useUpdateInventoryItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, itemId, data }) => {
      const response = await api.put(`/inventory/sessions/${sessionId}/items/${itemId}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inventory']);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la mise à jour');
    },
  });
};

const useValidateInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ sessionId, data }) => {
      const response = await api.post(`/inventory/sessions/${sessionId}/validate`, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['inventory']);
      queryClient.invalidateQueries(['products']);
      toast.success(`Inventaire validé - ${data.adjustments_count} ajustement(s) appliqué(s)`);
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de la validation');
    },
  });
};

const useCancelInventory = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId) => {
      const response = await api.delete(`/inventory/sessions/${sessionId}`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries(['inventory']);
      toast.success('Session d\'inventaire annulée');
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'annulation');
    },
  });
};

const useRefreshTheoretical = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId) => {
      const response = await api.post(`/inventory/sessions/${sessionId}/refresh-theoretical`);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries(['inventory']);
      if (data.updates_count > 0) {
        toast.success(`${data.updates_count} produit(s) mis à jour avec le stock actuel`);
      } else {
        toast.info('Tous les stocks théoriques sont déjà à jour');
      }
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || 'Erreur lors du recalcul');
    },
  });
};

const Inventory = () => {
  const { user } = useAuth();
  const { formatAmount } = useSettings();
  const queryClient = useQueryClient();
  
  // State
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [showValidateDialog, setShowValidateDialog] = useState(false);
  const [showHistoryDetailDialog, setShowHistoryDetailDialog] = useState(false);
  const [selectedHistorySession, setSelectedHistorySession] = useState(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState('');
  const [sessionName, setSessionName] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [filterMode, setFilterMode] = useState('all'); // all, uncounted, discrepancy
  const [filterCategoryId, setFilterCategoryId] = useState('all'); // Filtre par catégorie
  const [sortBy, setSortBy] = useState('name'); // name, discrepancy
  const [applyAdjustments, setApplyAdjustments] = useState(true);
  const [validationNotes, setValidationNotes] = useState('');
  const [historyYearFilter, setHistoryYearFilter] = useState(null);
  
  // Ref pour infinite scroll
  const historyLoadMoreRef = useRef(null);
  
  // Queries - Le rafraîchissement auto s'active uniquement si un inventaire est en cours
  const { data: currentSession, isLoading, isFetching, refetch: refetchInventory } = useCurrentInventory({ 
    enableAutoRefresh: false // On utilise un système plus intelligent ci-dessous
  });
  
  // History avec infinite scroll
  const { 
    data: historyPages, 
    fetchNextPage: fetchMoreHistory,
    hasNextPage: hasMoreHistory,
    isFetchingNextPage: isFetchingMoreHistory,
    isLoading: isLoadingHistory
  } = useInventoryHistory(historyYearFilter);
  
  // Flatten history data
  const historyData = useMemo(() => {
    if (!historyPages?.pages) return [];
    return historyPages.pages.flatMap(page => page.items || []);
  }, [historyPages]);
  
  // Available years from first page
  const availableYears = useMemo(() => {
    return historyPages?.pages?.[0]?.available_years || [];
  }, [historyPages]);
  
  const { data: categories = [] } = useCategories();
  const inventoryQueryClient = useQueryClient();
  
  // Observer pour infinite scroll
  useEffect(() => {
    if (!historyLoadMoreRef.current || !showHistoryDialog) return;
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMoreHistory && !isFetchingMoreHistory) {
          fetchMoreHistory();
        }
      },
      { threshold: 0.1 }
    );
    
    observer.observe(historyLoadMoreRef.current);
    return () => observer.disconnect();
  }, [showHistoryDialog, hasMoreHistory, isFetchingMoreHistory, fetchMoreHistory]);
  
  // Rafraîchissement intelligent: seulement si inventaire en cours et stock modifié
  const hasActiveSession = currentSession?.status === 'in_progress';
  const isRefreshing = isLoading || isFetching;
  
  useEffect(() => {
    if (!hasActiveSession) return;
    
    // Écouter les changements de stock via les invalidations de cache
    const unsubscribe = inventoryQueryClient.getQueryCache().subscribe((event) => {
      if (event?.type === 'updated' || event?.type === 'invalidated') {
        const queryKey = event?.query?.queryKey;
        // Rafraîchir l'inventaire si les ventes, retours ou stock changent
        if (queryKey && (
          queryKey[0] === 'sales' || 
          queryKey[0] === 'returns' ||
          queryKey[0] === 'stock' ||
          queryKey[0] === 'products'
        )) {
          // Délai pour éviter les rafraîchissements multiples
          setTimeout(() => {
            refetchInventory();
          }, 1000);
        }
      }
    });
    
    return () => unsubscribe();
  }, [hasActiveSession, inventoryQueryClient, refetchInventory]);
  
  // Bouton de rafraîchissement manuel
  const handleManualRefresh = useCallback(() => {
    refetchInventory();
  }, [refetchInventory]);
  
  // Mutations
  const createInventory = useCreateInventory();
  const updateItem = useUpdateInventoryItem();
  const validateInventory = useValidateInventory();
  const cancelInventory = useCancelInventory();
  const refreshTheoretical = useRefreshTheoretical();
  
  // Filtrer et trier les items
  const filteredItems = useMemo(() => {
    if (!currentSession?.items) return [];
    
    let items = [...currentSession.items];
    
    // Filtre par catégorie (utiliser category_name car category_id peut être absent)
    if (filterCategoryId && filterCategoryId !== 'all') {
      items = items.filter(item => item.category_name === filterCategoryId);
    }
    
    // Filtre par recherche
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      items = items.filter(item => 
        item.product_name.toLowerCase().includes(term) ||
        (item.barcode && item.barcode.toLowerCase().includes(term))
      );
    }
    
    // Filtre par mode
    if (filterMode === 'uncounted') {
      items = items.filter(item => item.actual_quantity === null);
    } else if (filterMode === 'discrepancy') {
      items = items.filter(item => item.discrepancy !== null && item.discrepancy !== 0);
    }
    
    // Tri
    if (sortBy === 'discrepancy') {
      items.sort((a, b) => Math.abs(b.discrepancy || 0) - Math.abs(a.discrepancy || 0));
    } else {
      items.sort((a, b) => a.product_name.localeCompare(b.product_name));
    }
    
    return items;
  }, [currentSession?.items, searchTerm, filterMode, filterCategoryId, sortBy]);
  
  // Récupérer les catégories présentes dans l'inventaire (par nom)
  const categoriesInInventory = useMemo(() => {
    if (!currentSession?.items) return [];
    const categoryNames = [...new Set(currentSession.items.map(item => item.category_name).filter(Boolean))];
    return categoryNames.sort();
  }, [currentSession?.items]);
  
  // Grouper les items par catégorie pour l'impression
  const itemsByCategory = useMemo(() => {
    if (!currentSession?.items) return {};
    const grouped = {};
    currentSession.items.forEach(item => {
      const catName = item.category_name || 'Sans catégorie';
      if (!grouped[catName]) grouped[catName] = [];
      grouped[catName].push(item);
    });
    // Trier les produits par nom dans chaque catégorie
    Object.keys(grouped).forEach(cat => {
      grouped[cat].sort((a, b) => a.product_name.localeCompare(b.product_name));
    });
    return grouped;
  }, [currentSession?.items]);
  
  // Fonction d'impression
  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    const sessionDate = currentSession?.created_at 
      ? new Date(currentSession.created_at).toLocaleDateString('fr-FR')
      : new Date().toLocaleDateString('fr-FR');
    
    let html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Fiche d'Inventaire - ${sessionDate}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; font-size: 12px; }
          h1 { text-align: center; font-size: 18px; margin-bottom: 5px; }
          h2 { font-size: 14px; background: #f0f0f0; padding: 8px; margin-top: 20px; margin-bottom: 10px; border-left: 4px solid #0d9488; }
          .header { text-align: center; margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 10px; }
          .header p { margin: 5px 0; color: #666; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
          th, td { border: 1px solid #333; padding: 8px; text-align: left; }
          th { background: #0d9488; color: white; font-weight: bold; }
          .col-product { width: 50%; }
          .col-actual { width: 25%; text-align: center; }
          .col-verified { width: 25%; text-align: center; }
          .actual-input { min-height: 25px; background: #fafafa; }
          .footer { margin-top: 30px; border-top: 1px solid #ccc; padding-top: 15px; }
          .signature { display: flex; justify-content: space-between; margin-top: 30px; }
          .signature-box { width: 45%; }
          .signature-line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; text-align: center; }
          @media print { 
            body { margin: 10px; }
            h2 { page-break-inside: avoid; }
            tr { page-break-inside: avoid; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>FICHE D'INVENTAIRE PHYSIQUE</h1>
          <p><strong>Session:</strong> ${currentSession?.name || 'Inventaire du ' + sessionDate}</p>
          <p><strong>Date:</strong> ${sessionDate}</p>
          <p><strong>Total produits:</strong> ${currentSession?.items?.length || 0}</p>
        </div>
    `;
    
    // Grouper par catégorie
    Object.keys(itemsByCategory).sort().forEach(categoryName => {
      const items = itemsByCategory[categoryName];
      html += `
        <h2>${categoryName} (${items.length} produits)</h2>
        <table>
          <thead>
            <tr>
              <th class="col-product">Produit</th>
              <th class="col-actual">Stock Réel</th>
              <th class="col-verified">Stock Réel vérifié</th>
            </tr>
          </thead>
          <tbody>
      `;
      
      items.forEach(item => {
        html += `
          <tr>
            <td class="col-product">${item.product_name}</td>
            <td class="col-actual actual-input"></td>
            <td class="col-verified actual-input"></td>
          </tr>
        `;
      });
      
      html += `
          </tbody>
        </table>
      `;
    });
    
    html += `
        <div class="footer">
          <div class="signature">
            <div class="signature-box">
              <div class="signature-line">Réalisé par</div>
            </div>
            <div class="signature-box">
              <div class="signature-line">Vérifié par</div>
            </div>
          </div>
        </div>
      </body>
      </html>
    `;
    
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.print();
  };
  
  // Compter les produits avec MAJ automatique du stock théorique
  const autoUpdatedCount = useMemo(() => {
    if (!currentSession?.items) return 0;
    return currentSession.items.filter(item => item.theoretical_movement_note).length;
  }, [currentSession?.items]);
  
  // Handlers
  const handleCreateSession = () => {
    createInventory.mutate({
      name: sessionName || null,
      category_id: selectedCategoryId || null,
    }, {
      onSuccess: () => {
        setShowCreateDialog(false);
        setSessionName('');
        setSelectedCategoryId('');
      }
    });
  };
  
  const handleCountItem = (itemId, value, note = null) => {
    if (!currentSession) return;
    
    const quantity = parseInt(value) || 0;
    updateItem.mutate({
      sessionId: currentSession.id,
      itemId,
      data: { actual_quantity: quantity, note: note }
    });
  };
  
  const handleValidate = () => {
    if (!currentSession) return;
    
    validateInventory.mutate({
      sessionId: currentSession.id,
      data: {
        apply_adjustments: true, // Toujours appliquer les ajustements
        validation_notes: validationNotes || null
      }
    }, {
      onSuccess: () => {
        setShowValidateDialog(false);
        setValidationNotes('');
      }
    });
  };
  
  const handleCancel = () => {
    if (!currentSession) return;
    if (window.confirm('Êtes-vous sûr de vouloir annuler cet inventaire ? Toutes les données seront perdues.')) {
      cancelInventory.mutate(currentSession.id);
    }
  };
  
  const canValidate = user?.role === 'admin' || user?.role === 'pharmacien';
  
  // Calcul de la progression avec protection contre NaN
  const countedItems = currentSession?.stats?.counted_items || 0;
  const totalItems = currentSession?.stats?.total_items || 0;
  const progress = totalItems > 0 ? Math.round((countedItems / totalItems) * 100) : 0;
  
  // Compter les écarts justifiés et non justifiés
  const discrepancyStats = useMemo(() => {
    if (!currentSession?.items) return { total: 0, justified: 0, unjustified: 0 };
    const itemsWithDiscrepancy = currentSession.items.filter(
      item => item.actual_quantity !== null && item.discrepancy !== 0
    );
    const justified = itemsWithDiscrepancy.filter(item => item.notes && item.notes.trim() !== '').length;
    return {
      total: itemsWithDiscrepancy.length,
      justified,
      unjustified: itemsWithDiscrepancy.length - justified
    };
  }, [currentSession?.items]);
  
  // Vérifier si tous les écarts sont justifiés
  const allDiscrepanciesJustified = discrepancyStats.total === 0 || discrepancyStats.unjustified === 0;
  
  // Conditions pour activer le bouton "Ajuster les stocks"
  const canAdjustStocks = progress === 100 && allDiscrepanciesJustified;
  
  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
        </div>
      </Layout>
    );
  }
  
  return (
    <Layout>
      <div className="space-y-6" data-testid="inventory-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
              <ClipboardList className="w-7 h-7 text-teal-600" />
              Inventaire Physique
            </h1>
            <p className="text-slate-500 mt-1">
              Comparaison stock théorique vs réel avec génération des écarts
            </p>
          </div>
          
          <div className="flex gap-2">
            {/* Bouton de rafraîchissement manuel - visible uniquement si inventaire en cours */}
            {hasActiveSession && (
              <Button
                variant="outline"
                onClick={handleManualRefresh}
                disabled={isRefreshing}
                className="rounded-full"
                title="Actualiser les données de stock"
              >
                <RefreshCw className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                Actualiser
              </Button>
            )}
            
            <Button
              variant="outline"
              onClick={() => setShowHistoryDialog(true)}
              className="rounded-full"
            >
              <History className="w-4 h-4 mr-2" />
              Historique
            </Button>
            
            {!currentSession && (
              <Button
                onClick={() => setShowCreateDialog(true)}
                className="bg-teal-600 hover:bg-teal-700 rounded-full"
                data-testid="new-inventory-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Nouvel inventaire
              </Button>
            )}
          </div>
        </div>
        
        {/* Session en cours */}
        {currentSession ? (
          <div className="space-y-6">
            {/* Alerte MAJ automatique */}
            {autoUpdatedCount > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
                <RefreshCw className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-amber-800">
                    Mouvements de stock détectés pendant l&apos;inventaire
                  </p>
                  <p className="text-sm text-amber-700 mt-1">
                    {autoUpdatedCount} produit{autoUpdatedCount > 1 ? 's ont' : ' a'} eu des mouvements de stock (ventes, approvisionnements, pertes...) 
                    pendant cet inventaire. Les quantités théoriques ont été automatiquement mises à jour.
                    Les produits concernés sont marqués avec <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-amber-100 rounded text-xs"><RefreshCw className="w-3 h-3" />MAJ auto</span>
                  </p>
                </div>
              </div>
            )}
            
            {/* Stats de la session */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
              <div className="flex flex-col lg:flex-row justify-between gap-6">
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">{currentSession.name}</h2>
                  <p className="text-sm text-slate-500">
                    Créé par {currentSession.created_by}
                  </p>
                </div>
                
                {/* Progress */}
                <div className="flex-1 max-w-md">
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-600">Progression</span>
                    <span className="font-medium">{countedItems}/{totalItems} ({progress}%)</span>
                  </div>
                  <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${progress === 100 ? 'bg-green-500' : 'bg-teal-500'}`}
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
                
                {/* Actions */}
                <div className="flex gap-2">
                  {canValidate && (
                    <Button
                      variant="outline"
                      onClick={() => refreshTheoretical.mutate(currentSession.id)}
                      disabled={refreshTheoretical.isPending}
                      className="text-amber-600 hover:bg-amber-50"
                      title="Recalculer toutes les quantités théoriques depuis le stock actuel"
                    >
                      {refreshTheoretical.isPending ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4 mr-2" />
                      )}
                      Recalculer stocks
                    </Button>
                  )}
                  {canValidate && (
                    <Button
                      onClick={() => setShowValidateDialog(true)}
                      className={canAdjustStocks ? "bg-green-600 hover:bg-green-700" : "bg-slate-400 cursor-not-allowed"}
                      disabled={!canAdjustStocks}
                      data-testid="adjust-stocks-btn"
                      title={
                        progress < 100 
                          ? `Inventaire incomplet (${progress}%)` 
                          : !allDiscrepanciesJustified 
                            ? "Tous les écarts doivent être justifiés" 
                            : "Ajuster les stocks"
                      }
                    >
                      <CheckCheck className="w-4 h-4 mr-2" />
                      Ajuster les stocks
                    </Button>
                  )}
                  {canValidate && (
                    <Button
                      variant="outline"
                      onClick={handleCancel}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <X className="w-4 h-4 mr-2" />
                      Annuler
                    </Button>
                  )}
                </div>
              </div>
              
              {/* Statistiques des écarts */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6 pt-6 border-t border-slate-200">
                <div className="text-center p-3 bg-slate-50 rounded-lg">
                  <p className="text-2xl font-bold text-slate-800">{currentSession.products_with_discrepancy}</p>
                  <p className="text-xs text-slate-500">Produits avec écart</p>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-600">+{currentSession.total_positive_discrepancy}</p>
                  <p className="text-xs text-green-600">Excédents (unités)</p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-600">-{currentSession.total_negative_discrepancy || 0}</p>
                  <p className="text-xs text-red-600">Manques (unités)</p>
                </div>
                <div className="text-center p-3 bg-amber-50 rounded-lg">
                  <p className={`text-2xl font-bold ${(currentSession.stats?.total_discrepancy_value || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {formatAmount(Math.abs(currentSession.stats?.total_discrepancy_value || 0))}
                  </p>
                  <p className="text-xs text-amber-600">Valeur des écarts</p>
                </div>
                <div className={`text-center p-3 rounded-lg ${discrepancyStats.unjustified > 0 ? 'bg-orange-50' : 'bg-green-50'}`}>
                  <p className={`text-2xl font-bold ${discrepancyStats.unjustified > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    {discrepancyStats.justified}/{discrepancyStats.total}
                  </p>
                  <p className={`text-xs ${discrepancyStats.unjustified > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    Écarts justifiés
                  </p>
                </div>
              </div>
            </div>
            
            {/* Filtres et recherche */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  placeholder="Rechercher par nom ou code-barres..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
              
              <div className="flex flex-wrap gap-2">
                {/* Filtre par catégorie */}
                <Select value={filterCategoryId} onValueChange={setFilterCategoryId}>
                  <SelectTrigger className="w-[180px]">
                    <SelectValue placeholder="Catégorie" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Toutes les catégories</SelectItem>
                    {categoriesInInventory.map(catName => (
                      <SelectItem key={catName} value={catName}>{catName}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                <select
                  value={filterMode}
                  onChange={(e) => setFilterMode(e.target.value)}
                  className="px-3 py-2 border border-slate-200 rounded-lg text-sm"
                >
                  <option value="all">Tous les produits</option>
                  <option value="uncounted">Non comptés</option>
                  <option value="discrepancy">Avec écart</option>
                </select>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSortBy(sortBy === 'name' ? 'discrepancy' : 'name')}
                >
                  <ArrowUpDown className="w-4 h-4 mr-1" />
                  {sortBy === 'name' ? 'A-Z' : 'Écarts'}
                </Button>
                
                {/* Bouton d'impression */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePrint}
                  className="text-teal-700 border-teal-300 hover:bg-teal-50"
                >
                  <Printer className="w-4 h-4 mr-1" />
                  Imprimer
                </Button>
              </div>
            </div>
            
            {/* Liste des produits */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Produit</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Stock Théorique</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Stock Réel</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Écart</th>
                      <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Explication</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 uppercase">Valeur Écart</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredItems.map((item) => (
                      <InventoryItemRow
                        key={item.product_id}
                        item={item}
                        onCount={(value, note) => handleCountItem(item.id, value, note)}
                        formatAmount={formatAmount}
                        isUpdating={updateItem.isPending}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
              
              {filteredItems.length === 0 && (
                <div className="p-8 text-center text-slate-500">
                  <Package className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                  <p>Aucun produit trouvé</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Pas de session en cours */
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
            <ClipboardList className="w-16 h-16 mx-auto mb-4 text-slate-300" />
            <h3 className="text-xl font-semibold text-slate-700 mb-2">Aucun inventaire en cours</h3>
            <p className="text-slate-500 mb-6">
              Créez une nouvelle session pour commencer l&apos;inventaire physique de vos produits.
            </p>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="bg-teal-600 hover:bg-teal-700"
            >
              <Plus className="w-4 h-4 mr-2" />
              Démarrer un inventaire
            </Button>
          </div>
        )}
        
        {/* Dialog: Créer une session */}
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <ClipboardList className="w-5 h-5 text-teal-600" />
                Nouvelle session d&apos;inventaire
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              <div>
                <Label>Nom de la session (optionnel)</Label>
                <Input
                  value={sessionName}
                  onChange={(e) => setSessionName(e.target.value)}
                  placeholder={`Inventaire du ${new Date().toLocaleDateString('fr-FR')}`}
                  className="mt-1"
                />
              </div>
              
              <div>
                <Label>Catégorie (optionnel)</Label>
                <select
                  value={selectedCategoryId}
                  onChange={(e) => setSelectedCategoryId(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-slate-200 rounded-lg"
                >
                  <option value="">Tous les produits</option>
                  {categories.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
                <p className="text-xs text-slate-500 mt-1">
                  Filtrer par catégorie pour un inventaire partiel
                </p>
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                Annuler
              </Button>
              <Button
                onClick={handleCreateSession}
                disabled={createInventory.isPending}
                className="bg-teal-600 hover:bg-teal-700"
              >
                {createInventory.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Créer la session
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Dialog: Ajuster les stocks */}
        <Dialog open={showValidateDialog} onOpenChange={setShowValidateDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-green-600" />
                Ajuster les stocks
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {currentSession && (
                <div className="p-4 bg-slate-50 rounded-lg">
                  <h4 className="font-medium text-slate-700 mb-2">Résumé des écarts</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500">Produits avec écart:</span>
                      <span className="font-medium ml-2">{currentSession.products_with_discrepancy || currentSession.stats?.items_with_discrepancy || 0}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Excédents:</span>
                      <span className="font-medium text-green-600 ml-2">+{currentSession.total_positive_discrepancy || 0}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Manques:</span>
                      <span className="font-medium text-red-600 ml-2">-{currentSession.total_negative_discrepancy || 0}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Valeur totale:</span>
                      <span className={`font-medium ml-2 ${(currentSession.stats?.total_discrepancy_value || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatAmount(currentSession.stats?.total_discrepancy_value || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  <strong>Action qui sera effectuée :</strong>
                  <br />
                  <span className="text-green-700">
                    Les stocks de tous les produits seront ajustés selon les quantités réelles comptées lors de l&apos;inventaire.
                  </span>
                </p>
              </div>
              
              <div>
                <Label>Notes de validation (optionnel)</Label>
                <textarea
                  value={validationNotes}
                  onChange={(e) => setValidationNotes(e.target.value)}
                  placeholder="Observations, commentaires..."
                  className="w-full mt-1 px-3 py-2 border border-slate-200 rounded-lg resize-none"
                  rows={3}
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowValidateDialog(false)}>
                Annuler
              </Button>
              <Button
                onClick={handleValidate}
                disabled={validateInventory.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                {validateInventory.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Confirmer l&apos;ajustement
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        
        {/* Dialog: Historique */}
        <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <History className="w-5 h-5 text-slate-600" />
                Historique des inventaires
              </DialogTitle>
            </DialogHeader>
            
            {/* Filtre par année */}
            <div className="flex items-center gap-4 py-2 border-b">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-600">Année:</span>
              </div>
              <Select
                value={historyYearFilter?.toString() || "all"}
                onValueChange={(value) => setHistoryYearFilter(value === "all" ? null : parseInt(value))}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Toutes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes</SelectItem>
                  {availableYears.map((year) => (
                    <SelectItem key={year} value={year.toString()}>{year}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <span className="text-sm text-slate-400">
                {historyData.length} inventaire(s)
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto py-4">
              {isLoadingHistory ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-teal-600" />
                </div>
              ) : historyData.length === 0 ? (
                <p className="text-center text-slate-500 py-8">Aucun inventaire passé</p>
              ) : (
                <div className="space-y-3">
                  {historyData.map((session) => (
                    <div 
                      key={session.id}
                      className={`p-4 rounded-lg border ${
                        session.status === 'completed' ? 'bg-green-50 border-green-200' :
                        session.status === 'cancelled' ? 'bg-red-50 border-red-200' :
                        'bg-amber-50 border-amber-200'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium text-slate-800">{session.name}</h4>
                          <p className="text-sm text-slate-500">
                            {new Date(session.created_at).toLocaleDateString('fr-FR')} par{' '}
                            {(() => {
                              const code = session.created_by || session.created_by_name || '-';
                              const isAdmin = code.startsWith('ADM');
                              const isPharma = code.startsWith('PHA');
                              const isCaissier = code.startsWith('CAI');
                              const colorClass = isAdmin ? 'text-purple-600 bg-purple-50' :
                                                isPharma ? 'text-teal-600 bg-teal-50' :
                                                isCaissier ? 'text-amber-600 bg-amber-50' :
                                                'text-slate-600 bg-slate-50';
                              return <span className={`font-bold px-2 py-0.5 rounded-full text-xs ${colorClass}`}>{code}</span>;
                            })()}
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          session.status === 'completed' ? 'bg-green-100 text-green-700' :
                          session.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                          'bg-amber-100 text-amber-700'
                        }`}>
                          {session.status === 'completed' ? 'Terminé' :
                           session.status === 'cancelled' ? 'Annulé' : 'En cours'}
                        </span>
                      </div>
                      
                      {session.status === 'completed' && (
                        <>
                          <div className="mt-3 grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-slate-500">Produits:</span>
                              <span className="font-medium ml-1">{session.stats?.total_items || session.total_products || 0}</span>
                            </div>
                            <div>
                              <span className="text-slate-500">Écarts:</span>
                              <span className="font-medium ml-1">{session.stats?.items_with_discrepancy || session.products_with_discrepancy || 0}</span>
                            </div>
                            <div>
                              <span className="text-green-600">+{session.total_positive_discrepancy || 0}</span>
                              <span className="text-slate-400 mx-1">/</span>
                              <span className="text-red-600">-{session.total_negative_discrepancy || 0}</span>
                            </div>
                            <div>
                              <span className={(session.stats?.total_discrepancy_value || 0) >= 0 ? 'text-green-600' : 'text-red-600'}>
                                {formatAmount(session.stats?.total_discrepancy_value || 0)}
                              </span>
                            </div>
                          </div>
                          <div className="mt-3 pt-3 border-t border-green-200">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedHistorySession(session);
                                setShowHistoryDetailDialog(true);
                              }}
                              className="text-teal-600 hover:bg-teal-50"
                            >
                              <Eye className="w-4 h-4 mr-2" />
                              Voir les détails
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                  
                  {/* Infinite scroll trigger */}
                  <div ref={historyLoadMoreRef} className="py-4 text-center">
                    {isFetchingMoreHistory && (
                      <div className="flex items-center justify-center gap-2 text-slate-500">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span className="text-sm">Chargement...</span>
                      </div>
                    )}
                    {!hasMoreHistory && historyData.length > 0 && (
                      <span className="text-sm text-slate-400">Fin de l'historique</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
        
        {/* Dialog: Détails d'un inventaire historique */}
        <Dialog open={showHistoryDetailDialog} onOpenChange={setShowHistoryDetailDialog}>
          <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-teal-600" />
                Détails de l'inventaire
              </DialogTitle>
            </DialogHeader>
            
            {selectedHistorySession && (
              <div className="flex-1 overflow-hidden flex flex-col">
                {/* En-tête */}
                <div className="p-4 bg-slate-50 rounded-lg mb-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500">Session:</span>
                      <span className="font-medium ml-1">{selectedHistorySession.name}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Date:</span>
                      <span className="font-medium ml-1">
                        {new Date(selectedHistorySession.validated_at || selectedHistorySession.created_at).toLocaleDateString('fr-FR')}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Validé par:</span>
                      <span className="font-medium ml-1">{selectedHistorySession.validated_by || '-'}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Valeur écarts:</span>
                      <span className={`font-medium ml-1 ${(selectedHistorySession.stats?.total_discrepancy_value || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatAmount(selectedHistorySession.stats?.total_discrepancy_value || 0)}
                      </span>
                    </div>
                  </div>
                  {selectedHistorySession.validation_notes && (
                    <div className="mt-3 pt-3 border-t border-slate-200">
                      <span className="text-slate-500 text-sm">Notes:</span>
                      <p className="text-sm text-slate-700 mt-1">{selectedHistorySession.validation_notes}</p>
                    </div>
                  )}
                </div>
                
                {/* Liste des produits avec écarts */}
                <div className="flex-1 overflow-auto">
                  <h4 className="font-medium text-slate-700 mb-2">Produits avec écarts</h4>
                  <table className="w-full text-sm">
                    <thead className="bg-slate-100 sticky top-0">
                      <tr>
                        <th className="px-3 py-2 text-left">Produit</th>
                        <th className="px-3 py-2 text-center">Stock théorique</th>
                        <th className="px-3 py-2 text-center">Stock réel</th>
                        <th className="px-3 py-2 text-center">Écart</th>
                        <th className="px-3 py-2 text-right">Valeur écart</th>
                        <th className="px-3 py-2 text-left">Explication</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {selectedHistorySession.items?.filter(item => item.discrepancy !== 0).map((item, index) => (
                        <tr key={index} className="hover:bg-slate-50">
                          <td className="px-3 py-2 font-medium">{item.product_name}</td>
                          <td className="px-3 py-2 text-center">{item.theoretical_quantity}</td>
                          <td className="px-3 py-2 text-center">{item.actual_quantity}</td>
                          <td className={`px-3 py-2 text-center font-medium ${item.discrepancy > 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {item.discrepancy > 0 ? '+' : ''}{item.discrepancy}
                          </td>
                          <td className={`px-3 py-2 text-right font-medium ${(item.discrepancy_value || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {item.discrepancy_value ? formatAmount(item.discrepancy_value) : '-'}
                          </td>
                          <td className="px-3 py-2 text-slate-600">{item.notes || '-'}</td>
                        </tr>
                      ))}
                      {(!selectedHistorySession.items || selectedHistorySession.items.filter(item => item.discrepancy !== 0).length === 0) && (
                        <tr>
                          <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                            Aucun écart enregistré pour cet inventaire
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowHistoryDetailDialog(false)}>
                Fermer
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

// Composant pour une ligne d'item d'inventaire
const InventoryItemRow = ({ item, onCount, formatAmount, isUpdating }) => {
  const [localValue, setLocalValue] = useState(item.actual_quantity ?? '');
  const [localNote, setLocalNote] = useState(item.notes || '');
  const [isEditing, setIsEditing] = useState(false);
  
  const handleBlur = () => {
    setIsEditing(false);
    if (localValue !== '' && parseInt(localValue) !== item.actual_quantity) {
      onCount(localValue, localNote);
    }
  };
  
  const handleNoteBlur = () => {
    // Sauvegarder la note seulement si elle a changé et qu'il y a un écart
    if (localNote !== (item.notes || '') && item.discrepancy !== 0) {
      onCount(item.actual_quantity, localNote);
    }
  };
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.target.blur();
    }
  };
  
  const isCounted = item.actual_quantity !== null;
  const hasDiscrepancy = isCounted && item.discrepancy !== 0;
  
  return (
    <tr className={`${isCounted ? '' : 'bg-amber-50/50'} hover:bg-slate-50 transition-colors`}>
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isCounted ? 'bg-green-500' : 'bg-amber-400'}`} />
          <div>
            <p className="font-medium text-slate-800">{item.product_name}</p>
            <p className="text-xs text-slate-500">
              {item.barcode && <span className="mr-2">{item.barcode}</span>}
              {item.category_name && <span className="text-slate-400">{item.category_name}</span>}
            </p>
          </div>
        </div>
      </td>
      
      <td className="px-4 py-3 text-center">
        <div className="flex flex-col items-center">
          <span className="font-mono text-lg text-slate-600">{item.theoretical_quantity}</span>
          {item.theoretical_movement_note && (
            <span className="text-xs text-amber-600 flex items-center gap-1" title={item.theoretical_movement_note}>
              <RefreshCw className="w-3 h-3" />
              MAJ auto
            </span>
          )}
        </div>
      </td>
      
      <td className="px-4 py-3 text-center">
        <input
          type="number"
          min="0"
          value={localValue}
          onChange={(e) => setLocalValue(e.target.value)}
          onFocus={() => setIsEditing(true)}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          className={`w-20 px-2 py-1 text-center font-mono text-lg border rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 ${
            isCounted ? 'border-green-300 bg-green-50' : 'border-amber-300 bg-white'
          }`}
          placeholder="—"
        />
      </td>
      
      <td className="px-4 py-3 text-center">
        {isCounted && (
          <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium ${
            item.discrepancy === 0 ? 'bg-slate-100 text-slate-600' :
            item.discrepancy > 0 ? 'bg-green-100 text-green-700' :
            'bg-red-100 text-red-700'
          }`}>
            {item.discrepancy === 0 ? (
              <CheckCircle2 className="w-3 h-3" />
            ) : item.discrepancy > 0 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {item.discrepancy > 0 ? '+' : ''}{item.discrepancy}
          </span>
        )}
      </td>
      
      <td className="px-4 py-3 text-center">
        {hasDiscrepancy ? (
          <input
            type="text"
            value={localNote}
            onChange={(e) => setLocalNote(e.target.value)}
            onBlur={handleNoteBlur}
            onKeyDown={handleKeyDown}
            className={`w-full max-w-[200px] px-2 py-1 text-sm border rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500 ${
              localNote ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
            }`}
            placeholder="Justifier l'écart..."
          />
        ) : (
          <span className="text-slate-400 text-sm">—</span>
        )}
      </td>
      
      <td className="px-4 py-3 text-right">
        {isCounted && (
          item.discrepancy === 0 ? (
            <span className="font-medium text-slate-600">0 GNF</span>
          ) : item.unit_cost === 0 ? (
            <span className="text-xs text-slate-400 italic" title="Le prix de ce produit n'est pas défini dans le système">
              Prix non défini
            </span>
          ) : (
            <span className={`font-medium ${item.discrepancy_value >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {item.discrepancy_value >= 0 ? '+' : ''}{formatAmount(item.discrepancy_value)}
            </span>
          )
        )}
      </td>
    </tr>
  );
};

export default Inventory;
