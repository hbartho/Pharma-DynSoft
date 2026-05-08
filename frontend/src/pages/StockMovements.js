import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { 
  History, Search, Package, TrendingUp, TrendingDown, 
  ArrowRightLeft, Filter, Calendar, Download, Loader2,
  ShoppingCart, RotateCcw, Truck, ClipboardList, PackageX,
  AlertTriangle, RefreshCw, Timer
} from 'lucide-react';
import api from '../services/api';
import { useSettings } from '../contexts/SettingsContext';
import { useProducts } from '../hooks/useProducts';
import { useAuth } from '../contexts/AuthContext';
import { useShiftEligibility } from '../hooks/useShiftSchedules';

// Types de mouvements avec leurs configurations (alignés avec le backend)
const MOVEMENT_TYPES = {
  in: { 
    label: 'Entrée', 
    icon: TrendingUp, 
    color: 'green',
    bgColor: 'bg-green-50',
    textColor: 'text-green-700',
    borderColor: 'border-green-200',
    isOutflow: false  // Entrée de stock
  },
  out: { 
    label: 'Sortie', 
    icon: TrendingDown, 
    color: 'red',
    bgColor: 'bg-red-50',
    textColor: 'text-red-700',
    borderColor: 'border-red-200',
    isOutflow: true  // Sortie de stock
  },
  return: { 
    label: 'Retour', 
    icon: RotateCcw, 
    color: 'blue',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-700',
    borderColor: 'border-blue-200',
    isOutflow: false  // Entrée de stock
  },
  loss: { 
    label: 'Perte', 
    icon: PackageX, 
    color: 'amber',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-700',
    borderColor: 'border-amber-200',
    isOutflow: true  // Sortie de stock
  },
  adjustment: { 
    label: 'Ajustement', 
    icon: ArrowRightLeft, 
    color: 'purple',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-700',
    borderColor: 'border-purple-200',
    isOutflow: null  // Peut être les deux
  },
};

const useStockMovementsInfinite = (filters) => {
  return useInfiniteQuery({
    queryKey: ['stock-movements', 'infinite', filters],
    queryFn: async ({ pageParam = 1 }) => {
      const params = new URLSearchParams();
      params.append('page', pageParam.toString());
      params.append('limit', '30');
      if (filters.productId) params.append('product_id', filters.productId);
      if (filters.movementType && filters.movementType !== 'all') {
        params.append('movement_type', filters.movementType);
      }
      if (filters.search) params.append('search', filters.search);
      
      const response = await api.get(`/stock/movements/paginated?${params.toString()}`);
      return response.data;
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.pages) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 30 * 1000,
  });
};

const StockMovements = () => {
  const { formatAmount } = useSettings();
  const { data: products = [] } = useProducts();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const loadMoreRef = useRef(null);
  
  // Vérifier l'éligibilité de planification
  const { data: shiftEligibility } = useShiftEligibility();
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedProduct, setSelectedProduct] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  
  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchTerm), 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);
  
  // Query avec infinite scroll
  const { 
    data: movementsData, 
    isLoading, 
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch 
  } = useStockMovementsInfinite({
    productId: selectedProduct,
    movementType: selectedType,
    search: debouncedSearch,
  });
  
  const movements = movementsData?.pages?.flatMap(page => page.items) || [];
  const totalMovements = movementsData?.pages?.[0]?.total || 0;
  const apiStats = movementsData?.pages?.[0]?.stats || null;
  
  // Intersection Observer pour infinite scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    if (loadMoreRef.current) observer.observe(loadMoreRef.current);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  
  // Filtered movements (local filtering for date only, rest is server-side)
  const filteredMovements = useMemo(() => {
    let filtered = [...movements];
    
    // Date filters (local)
    if (dateFrom) {
      const from = new Date(dateFrom);
      filtered = filtered.filter(m => new Date(m.created_at) >= from);
    }
    if (dateTo) {
      const to = new Date(dateTo);
      to.setHours(23, 59, 59);
      filtered = filtered.filter(m => new Date(m.created_at) <= to);
    }
    
    return filtered;
  }, [movements, searchTerm, dateFrom, dateTo]);
  
  // Helper pour obtenir la quantité avec le bon signe
  const getSignedQuantity = (movement) => {
    const rawQty = movement.movement_quantity || movement.quantity || 0;
    const config = MOVEMENT_TYPES[movement.movement_type] || {};
    
    // Pour les ajustements (isOutflow === null), utiliser le signe original de la quantité
    if (config.isOutflow === null) {
      // La quantité est déjà signée pour les ajustements (positif = excédent, négatif = manque)
      return rawQty;
    }
    
    // Pour les autres types, forcer le signe selon isOutflow
    const absQty = Math.abs(rawQty);
    if (config.isOutflow === true) {
      return -absQty;  // Sortie = négatif
    } else if (config.isOutflow === false) {
      return absQty;   // Entrée = positif
    }
    
    // Fallback: utiliser stock_before/after si disponible
    if (movement.stock_before !== undefined && movement.stock_after !== undefined) {
      return movement.stock_after - movement.stock_before;
    }
    
    return absQty;
  };

  // Statistics
  const stats = useMemo(() => {
    const result = {
      totalIn: 0,
      totalOut: 0,
      byType: {}
    };
    
    filteredMovements.forEach(m => {
      const qty = getSignedQuantity(m);
      if (qty > 0) result.totalIn += qty;
      else result.totalOut += Math.abs(qty);
      
      const type = m.movement_type || 'unknown';
      if (!result.byType[type]) result.byType[type] = { count: 0, quantity: 0 };
      result.byType[type].count++;
      result.byType[type].quantity += qty;
    });
    
    return result;
  }, [filteredMovements]);
  
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  const getMovementConfig = (type) => {
    return MOVEMENT_TYPES[type] || MOVEMENT_TYPES.adjustment;
  };
  
  const clearFilters = () => {
    setSearchTerm('');
    setSelectedProduct('');
    setSelectedType('');
    setDateFrom('');
    setDateTo('');
  };
  
  return (
    <Layout>
      <div className="space-y-6" data-testid="stock-movements-page">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-3">
              <History className="w-7 h-7 text-teal-600" />
              Historique des Mouvements
            </h1>
            <p className="text-slate-500 mt-1">
              Traçabilité complète des entrées et sorties de stock
            </p>
          </div>
          
          <Button
            variant="outline"
            onClick={() => refetch()}
            className="rounded-full"
            disabled={!isAdmin && !isWithinScheduledHours}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Actualiser
          </Button>
        </div>
        
        {/* Message de restriction pour utilisateurs hors horaires */}
        {!isAdmin && !isWithinScheduledHours ? (
          <div className="p-6 bg-amber-50 rounded-xl border border-amber-200">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Timer className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-800">Accès restreint - Hors horaires de travail</h3>
                <p className="text-sm text-amber-700 mt-1">
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux mouvements de stock en dehors de vos horaires planifiés.'}
                </p>
                {shiftEligibility?.schedule && (
                  <p className="text-sm text-amber-600 mt-2">
                    <strong>Horaires prévus :</strong> {shiftEligibility.schedule.start_time} - {shiftEligibility.schedule.end_time}
                  </p>
                )}
                {shiftEligibility?.current_time && (
                  <p className="text-xs text-amber-500 mt-1">
                    Heure actuelle : {shiftEligibility.current_time}
                  </p>
                )}
              </div>
            </div>
          </div>
        ) : (
        <>
        {/* Statistics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-100 rounded-lg">
                <ArrowRightLeft className="w-5 h-5 text-slate-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{totalMovements}</p>
                <p className="text-xs text-slate-500">Mouvements</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-green-200 p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">+{apiStats?.total_in ?? stats.totalIn}</p>
                <p className="text-xs text-slate-500">Entrées</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-red-200 p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <TrendingDown className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">-{apiStats?.total_out ?? stats.totalOut}</p>
                <p className="text-xs text-slate-500">Sorties</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-teal-100 rounded-lg">
                <Package className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className={`text-2xl font-bold ${(apiStats?.net_balance ?? (stats.totalIn - stats.totalOut)) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(apiStats?.net_balance ?? (stats.totalIn - stats.totalOut)) >= 0 ? '+' : ''}{apiStats?.net_balance ?? (stats.totalIn - stats.totalOut)}
                </p>
                <p className="text-xs text-slate-500">Solde net</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <div className="flex flex-wrap gap-4">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                placeholder="Rechercher produit, référence..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            
            {/* Product filter */}
            <select
              value={selectedProduct}
              onChange={(e) => setSelectedProduct(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm min-w-[180px]"
            >
              <option value="">Tous les produits</option>
              {products.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            
            {/* Type filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm min-w-[180px]"
            >
              <option value="">Tous les types</option>
              {Object.entries(MOVEMENT_TYPES).map(([key, config]) => (
                <option key={key} value={key}>{config.label}</option>
              ))}
            </select>
            
            {/* Date filters */}
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-400" />
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-36"
                placeholder="Du"
              />
              <span className="text-slate-400">→</span>
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-36"
                placeholder="Au"
              />
            </div>
            
            {/* Clear filters */}
            {(searchTerm || selectedProduct || selectedType || dateFrom || dateTo) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-slate-500"
              >
                Effacer filtres
              </Button>
            )}
          </div>
        </div>
        
        {/* Movements List */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          {isLoading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
            </div>
          ) : filteredMovements.length === 0 ? (
            <div className="p-12 text-center">
              <History className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p className="text-slate-500">Aucun mouvement de stock trouvé</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Date</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Produit</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-slate-600 uppercase">Quantité</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Référence</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase">Par</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredMovements.map((movement, index) => {
                    const config = getMovementConfig(movement.movement_type);
                    const Icon = config.icon;
                    const qty = getSignedQuantity(movement);
                    const isPositive = qty > 0;
                    
                    return (
                      <tr key={movement.id || index} className="hover:bg-slate-50 transition-colors">
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {formatDate(movement.created_at)}
                        </td>
                        <td className="px-4 py-3">
                          <div className={`inline-flex items-center gap-2 px-2 py-1 rounded-full text-xs font-medium ${config.bgColor} ${config.textColor}`}>
                            <Icon className="w-3 h-3" />
                            {config.label}
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <p className="font-medium text-slate-800">{movement.product_name}</p>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold ${
                            isPositive ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                            {isPositive ? '+' : ''}{qty}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-600">
                          {movement.reference || movement.notes || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-slate-500">
                          {movement.created_by || '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          
          {/* Infinite Scroll Loader */}
          {movements.length > 0 && (
            <div className="flex flex-col items-center gap-4 py-6 border-t border-slate-100">
              <p className="text-sm text-slate-600">
                {movements.length} sur {totalMovements} mouvements affichés
              </p>
              <div ref={loadMoreRef} className="h-2 w-full" />
              {isFetchingNextPage && (
                <div className="flex items-center gap-2 text-teal-600">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span className="text-sm">Chargement...</span>
                </div>
              )}
              {hasNextPage && !isFetchingNextPage && (
                <Button variant="outline" onClick={() => fetchNextPage()} className="rounded-full">
                  Charger plus de mouvements
                </Button>
              )}
              {!hasNextPage && movements.length > 0 && (
                <p className="text-sm text-slate-400">✓ Tous les mouvements ont été chargés</p>
              )}
            </div>
          )}
        </div>
        
        {/* Legend */}
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
          <h4 className="text-sm font-semibold text-slate-700 mb-3">Légende des types de mouvements</h4>
          <div className="flex flex-wrap gap-3">
            {Object.entries(MOVEMENT_TYPES).map(([key, config]) => {
              const Icon = config.icon;
              return (
                <div 
                  key={key}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs ${config.bgColor} ${config.textColor} border ${config.borderColor}`}
                >
                  <Icon className="w-3 h-3" />
                  {config.label}
                </div>
              );
            })}
          </div>
        </div>
        </>
        )}
      </div>
    </Layout>
  );
};

export default StockMovements;
