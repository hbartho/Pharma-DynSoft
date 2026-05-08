import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { 
  Package, AlertTriangle, Clock, CheckCircle2, XCircle, 
  Plus, Search, Loader2, TrendingDown, BarChart3, History,
  PackageX, Trash2, ShieldAlert, HelpCircle, RefreshCw, Timer, Truck
} from 'lucide-react';
import { toast } from 'sonner';
import { useSettings } from '../contexts/SettingsContext';
import { useAuth } from '../contexts/AuthContext';
import { useProducts } from '../hooks/useProducts';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';
import { 
  useLossReasons, 
  usePendingLosses, 
  useLossesStats,
  useDeclareLoss,
  useValidateLoss 
} from '../hooks/useStock';
import { useStockLossesInfinite } from '../hooks/useInfiniteScroll';

const StockLosses = () => {
  const { formatAmount } = useSettings();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const loadMoreRef = useRef(null);
  
  // Vérifier si l'utilisateur peut effectuer des opérations (admin exempté)
  const { data: currentShift } = useCurrentShift();
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // Vérifier l'éligibilité de planification (pour restreindre l'accès hors horaires)
  const { data: shiftEligibility } = useShiftEligibility();
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  const [activeTab, setActiveTab] = useState('pending');
  const [showDeclareDialog, setShowDeclareDialog] = useState(false);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [selectedLoss, setSelectedLoss] = useState(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  
  // Formulaire de déclaration
  const [declareForm, setDeclareForm] = useState({
    productId: '',
    quantity: '',
    reason: '',
    reasonDetails: '',
    notes: '',
  });
  const [productSearch, setProductSearch] = useState('');
  const [showProductResults, setShowProductResults] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  
  // Filtres historique
  const [historyFilters, setHistoryFilters] = useState({
    status: '',
    reason: '',
    dateFrom: '',
    dateTo: '',
  });
  
  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Infinite scroll pour l'historique des pertes avec filtres
  const { 
    data: lossesData,
    isLoading: historyLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = useStockLossesInfinite({
    limit: 20,
    search: debouncedSearch,
    status: historyFilters.status || undefined,
    reason: historyFilters.reason || undefined,
    date_from: historyFilters.dateFrom || undefined,
    date_to: historyFilters.dateTo || undefined,
  });
  
  const lossesHistory = lossesData?.pages?.flatMap(page => page.items) || [];
  const totalLosses = lossesData?.pages?.[0]?.total || 0;
  
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
  
  // Queries
  const { data: lossReasons = [] } = useLossReasons();
  const { data: pendingLosses = [], isLoading: pendingLoading } = usePendingLosses();
  const { data: stats = {}, isLoading: statsLoading } = useLossesStats('month');
  const { data: products = [] } = useProducts();
  
  // Mutations
  const declareLoss = useDeclareLoss();
  const validateLoss = useValidateLoss();
  
  // Filtrer les produits avec stock
  const productsWithStock = products.filter(p => p.stock > 0);
  
  // Filtrer les produits selon la recherche
  const filteredProducts = productSearch.length >= 1
    ? productsWithStock.filter(p => 
        p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
        (p.sku && p.sku.toLowerCase().includes(productSearch.toLowerCase())) ||
        (p.internal_reference && p.internal_reference.toLowerCase().includes(productSearch.toLowerCase()))
      )
    : [];
  
  // Sélectionner un produit
  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setDeclareForm({...declareForm, productId: product.id});
    setProductSearch(product.name);
    setShowProductResults(false);
  };
  
  // Reset du formulaire
  const resetDeclareForm = () => {
    setDeclareForm({
      productId: '',
      quantity: '',
      reason: '',
      reasonDetails: '',
      notes: '',
    });
    setProductSearch('');
    setSelectedProduct(null);
    setShowProductResults(false);
  };
  
  // Formater la date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };
  
  // Soumettre la déclaration
  const handleSubmitDeclaration = async (e) => {
    e.preventDefault();
    
    if (!declareForm.productId) {
      toast.error('Veuillez sélectionner un produit');
      return;
    }
    if (!declareForm.quantity || parseInt(declareForm.quantity) <= 0) {
      toast.error('Veuillez saisir une quantité valide');
      return;
    }
    if (!declareForm.reason) {
      toast.error('Veuillez sélectionner un motif');
      return;
    }
    if (!declareForm.reasonDetails || declareForm.reasonDetails.trim().length === 0) {
      toast.error('Veuillez fournir une explication détaillée');
      return;
    }
    
    declareLoss.mutate(
      {
        productId: declareForm.productId,
        quantity: parseInt(declareForm.quantity),
        reason: declareForm.reason,
        reasonDetails: declareForm.reasonDetails,
        notes: declareForm.notes,
      },
      {
        onSuccess: (data) => {
          toast.success(data.message || 'Perte déclarée avec succès');
          setShowDeclareDialog(false);
          resetDeclareForm();
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors de la déclaration');
        },
      }
    );
  };
  
  // Vérifier si le formulaire est valide pour activer le bouton
  const isFormValid = declareForm.productId && 
    declareForm.quantity && 
    parseInt(declareForm.quantity) > 0 && 
    declareForm.reason && 
    declareForm.reasonDetails && 
    declareForm.reasonDetails.trim().length > 0;
  
  // Valider une perte
  const handleValidate = (loss) => {
    validateLoss.mutate(
      { lossId: loss.id, action: 'validate' },
      {
        onSuccess: (data) => {
          toast.success(data.message || 'Perte validée');
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors de la validation');
        },
      }
    );
  };
  
  // Rejeter une perte
  const handleReject = () => {
    if (!rejectionReason.trim()) {
      toast.error('Veuillez saisir une raison de rejet');
      return;
    }
    
    validateLoss.mutate(
      { lossId: selectedLoss.id, action: 'reject', rejectionReason },
      {
        onSuccess: (data) => {
          toast.success(data.message || 'Perte rejetée');
          setShowRejectDialog(false);
          setSelectedLoss(null);
          setRejectionReason('');
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors du rejet');
        },
      }
    );
  };
  
  // Icône du motif
  const getReasonIcon = (reason) => {
    switch (reason) {
      // Codes anglais
      case 'expired': return <Clock className="w-4 h-4 text-red-500" />;
      case 'damaged': return <PackageX className="w-4 h-4 text-orange-500" />;
      case 'theft': return <ShieldAlert className="w-4 h-4 text-purple-500" />;
      case 'inventory_adjustment': return <HelpCircle className="w-4 h-4 text-blue-500" />;
      case 'broken': return <PackageX className="w-4 h-4 text-orange-600" />;
      case 'returned_supplier': return <Truck className="w-4 h-4 text-teal-500" />;
      case 'other': return <HelpCircle className="w-4 h-4 text-slate-500" />;
      // Labels français (données existantes)
      case 'Produit périmé': return <Clock className="w-4 h-4 text-red-500" />;
      case 'Produit endommagé': return <PackageX className="w-4 h-4 text-orange-500" />;
      case 'Vol': return <ShieldAlert className="w-4 h-4 text-purple-500" />;
      case 'Ajustement inventaire': return <HelpCircle className="w-4 h-4 text-blue-500" />;
      case 'Casse': return <PackageX className="w-4 h-4 text-orange-600" />;
      case 'Retour fournisseur': return <Truck className="w-4 h-4 text-teal-500" />;
      case 'Autre': return <HelpCircle className="w-4 h-4 text-slate-500" />;
      default: return <AlertTriangle className="w-4 h-4 text-slate-500" />;
    }
  };
  
  // Badge de statut
  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700"><Clock className="w-3 h-3" /> En attente</span>;
      case 'validated':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700"><CheckCircle2 className="w-3 h-3" /> Validée</span>;
      case 'rejected':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700"><XCircle className="w-3 h-3" /> Rejetée</span>;
      default:
        return null;
    }
  };
  
  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Gestion des Pertes
            </h1>
            <p className="text-slate-500 mt-1">Déclarez et gérez les pertes de stock</p>
          </div>
          <Button 
            onClick={() => setShowDeclareDialog(true)}
            className="bg-red-600 hover:bg-red-700"
            data-testid="declare-loss-btn"
            disabled={!canOperate}
            title={!canOperate ? shiftBlockReason : ""}
          >
            <Plus className="w-4 h-4 mr-2" />
            Déclarer une perte
          </Button>
        </div>
        
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">En attente</p>
                <p className="text-xl font-bold text-slate-900">{stats.pending_count || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded-lg">
                <TrendingDown className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Pertes (30 jours)</p>
                <p className="text-xl font-bold text-slate-900">{stats.total_count || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <Package className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Qté perdue (30j)</p>
                <p className="text-xl font-bold text-slate-900">{stats.total_quantity || 0}</p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <BarChart3 className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-slate-500">Valeur perdue (30j)</p>
                <p className="text-xl font-bold text-slate-900">{formatAmount(stats.total_value || 0)}</p>
              </div>
            </div>
          </div>
        </div>
        
        {/* Message de restriction pour utilisateurs hors horaires */}
        {!isWithinScheduledHours ? (
          <div className="p-6 bg-amber-50 rounded-xl border border-amber-200">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Timer className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-800">Accès restreint - Hors horaires de travail</h3>
                <p className="text-sm text-amber-700 mt-1">
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder à la gestion des pertes en dehors de vos horaires planifiés.'}
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
        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-slate-100 p-1 rounded-lg">
            <TabsTrigger value="pending" className="rounded-md data-[state=active]:bg-white">
              <Clock className="w-4 h-4 mr-2" />
              En attente ({pendingLosses.length})
            </TabsTrigger>
            <TabsTrigger value="history" className="rounded-md data-[state=active]:bg-white">
              <History className="w-4 h-4 mr-2" />
              Historique
            </TabsTrigger>
            <TabsTrigger value="stats" className="rounded-md data-[state=active]:bg-white">
              <BarChart3 className="w-4 h-4 mr-2" />
              Statistiques
            </TabsTrigger>
          </TabsList>
          
          {/* TAB: En attente */}
          <TabsContent value="pending" className="space-y-4 mt-6">
            {pendingLoading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
              </div>
            ) : pendingLosses.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-300 mx-auto mb-3" />
                <p className="text-slate-500">Aucune perte en attente de validation</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Produit</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Quantité</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Motif</th>
                      <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900">Valeur est.</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Déclaré par</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Date</th>
                      {isAdmin && (
                        <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Actions</th>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {pendingLosses.map((loss) => (
                      <tr key={loss.id} className="hover:bg-amber-50 transition-colors">
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-medium text-slate-900">{loss.product_name}</p>
                            {loss.product_sku && (
                              <p className="text-xs text-slate-500">{loss.product_sku}</p>
                            )}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className="font-bold text-red-600">-{loss.quantity}</span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-2">
                            {getReasonIcon(loss.reason)}
                            <span className="text-sm">{loss.reason_label}</span>
                          </div>
                          {loss.reason_details && (
                            <p className="text-xs text-slate-500 text-center mt-1">{loss.reason_details}</p>
                          )}
                        </td>
                        <td className="px-6 py-4 text-right text-slate-600">
                          {formatAmount(loss.estimated_value || 0)}
                        </td>
                        <td className="px-6 py-4 text-slate-600">
                          {loss.declared_by_name || '-'}
                        </td>
                        <td className="px-6 py-4 text-slate-500 text-sm">
                          {formatDate(loss.created_at)}
                        </td>
                        {isAdmin && (
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                size="sm"
                                onClick={() => handleValidate(loss)}
                                className="bg-green-600 hover:bg-green-700"
                                disabled={validateLoss.isPending}
                                data-testid={`validate-loss-${loss.id}`}
                              >
                                <CheckCircle2 className="w-4 h-4 mr-1" />
                                Valider
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedLoss(loss);
                                  setShowRejectDialog(true);
                                }}
                                className="text-red-600 border-red-200 hover:bg-red-50"
                                disabled={validateLoss.isPending}
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Rejeter
                              </Button>
                            </div>
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </TabsContent>
          
          {/* TAB: Historique */}
          <TabsContent value="history" className="space-y-4 mt-6">
            {/* Filtres */}
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div>
                  <Label className="text-xs text-slate-500">Statut</Label>
                  <Select 
                    value={historyFilters.status || 'all'} 
                    onValueChange={(v) => setHistoryFilters({...historyFilters, status: v === 'all' ? '' : v})}
                  >
                    <SelectTrigger className="h-9 mt-1">
                      <SelectValue placeholder="Tous" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les statuts</SelectItem>
                      <SelectItem value="validated">Validées</SelectItem>
                      <SelectItem value="rejected">Rejetées</SelectItem>
                      <SelectItem value="pending">En attente</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label className="text-xs text-slate-500">Motif</Label>
                  <Select 
                    value={historyFilters.reason || 'all'} 
                    onValueChange={(v) => setHistoryFilters({...historyFilters, reason: v === 'all' ? '' : v})}
                  >
                    <SelectTrigger className="h-9 mt-1">
                      <SelectValue placeholder="Tous" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les motifs</SelectItem>
                      {lossReasons.map((r) => (
                        <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div>
                  <Label className="text-xs text-slate-500">Date début</Label>
                  <Input
                    type="date"
                    value={historyFilters.dateFrom}
                    onChange={(e) => setHistoryFilters({...historyFilters, dateFrom: e.target.value})}
                    className="h-9 mt-1"
                  />
                </div>
                
                <div>
                  <Label className="text-xs text-slate-500">Date fin</Label>
                  <Input
                    type="date"
                    value={historyFilters.dateTo}
                    onChange={(e) => setHistoryFilters({...historyFilters, dateTo: e.target.value})}
                    className="h-9 mt-1"
                  />
                </div>
                
                <div className="flex items-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setHistoryFilters({ status: '', reason: '', dateFrom: '', dateTo: '' })}
                    className="h-9 w-full"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Réinitialiser
                  </Button>
                </div>
              </div>
            </div>
            
            {historyLoading && lossesHistory.length === 0 ? (
              <div className="flex justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-slate-400" />
              </div>
            ) : lossesHistory.length === 0 ? (
              <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
                <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500">Aucune perte dans l&apos;historique</p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Date</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Produit</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Quantité</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Motif</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Statut</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Traité par</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {lossesHistory.map((loss) => (
                      <tr 
                        key={loss.id} 
                        className={`transition-colors ${
                          loss.status === 'rejected' ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="px-6 py-4 text-slate-500 text-sm">
                          {formatDate(loss.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <p className="font-medium text-slate-900">{loss.product_name}</p>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <span className={`font-bold ${loss.status === 'validated' ? 'text-red-600' : 'text-slate-400'}`}>
                            -{loss.quantity}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-center gap-2">
                            {getReasonIcon(loss.reason)}
                            <span className="text-sm">{loss.reason_label}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {getStatusBadge(loss.status)}
                          {loss.status === 'rejected' && loss.rejection_reason && (
                            <p className="text-xs text-red-500 mt-1">{loss.rejection_reason}</p>
                          )}
                        </td>
                        <td className="px-6 py-4 text-slate-600 text-sm">
                          {loss.validated_by_name || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                
                {/* Infinite Scroll Loader */}
                <div className="flex flex-col items-center gap-4 py-6 border-t border-slate-100">
                  <p className="text-sm text-slate-600">
                    {lossesHistory.length} sur {totalLosses} pertes affichées
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
                      Charger plus de pertes
                    </Button>
                  )}
                  {!hasNextPage && lossesHistory.length > 0 && (
                    <p className="text-sm text-slate-400">✓ Toutes les pertes ont été chargées</p>
                  )}
                </div>
              </div>
            )}
          </TabsContent>
          
          {/* TAB: Statistiques */}
          <TabsContent value="stats" className="space-y-4 mt-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6">
              <h3 className="font-semibold text-slate-900 mb-4">Répartition par motif (ce mois)</h3>
              
              {stats.by_reason && Object.keys(stats.by_reason).length > 0 ? (
                <div className="space-y-4">
                  {Object.entries(stats.by_reason).map(([code, data]) => (
                    <div key={code} className="flex items-center gap-4">
                      <div className="flex items-center gap-2 w-40">
                        {getReasonIcon(code)}
                        <span className="text-sm font-medium">{data.label}</span>
                      </div>
                      <div className="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                        <div 
                          className="h-full bg-red-500 rounded-full transition-all"
                          style={{ 
                            width: `${stats.total_quantity > 0 ? (data.quantity / stats.total_quantity * 100) : 0}%` 
                          }}
                        />
                      </div>
                      <div className="w-32 text-right">
                        <span className="text-sm font-bold text-slate-900">{data.quantity} unités</span>
                        <p className="text-xs text-slate-500">{data.count} déclaration(s)</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-500 text-center py-8">Aucune perte validée ce mois</p>
              )}
            </div>
          </TabsContent>
        </Tabs>
        </>
        )}
      </div>
      
      {/* Dialog: Déclarer une perte */}
      <Dialog open={showDeclareDialog} onOpenChange={(open) => {
        setShowDeclareDialog(open);
        if (!open) resetDeclareForm();
      }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <AlertTriangle className="w-5 h-5" />
              Déclarer une perte
            </DialogTitle>
          </DialogHeader>
          
          <form onSubmit={handleSubmitDeclaration} className="space-y-4">
            {/* Recherche Produit */}
            <div className="relative">
              <Label>Produit <span className="text-red-500">*</span></Label>
              <div className="relative mt-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <Input
                  type="text"
                  value={productSearch}
                  onChange={(e) => {
                    setProductSearch(e.target.value);
                    setShowProductResults(true);
                    if (!e.target.value) {
                      setSelectedProduct(null);
                      setDeclareForm({...declareForm, productId: ''});
                    }
                  }}
                  onFocus={() => setShowProductResults(true)}
                  placeholder="Rechercher un produit..."
                  className="pl-10"
                  data-testid="loss-product-search"
                />
              </div>
              
              {/* Résultats de recherche */}
              {showProductResults && productSearch.length >= 1 && (
                <div className="absolute z-[100] w-full mt-1 bg-white border border-slate-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {filteredProducts.length === 0 ? (
                    <div className="p-3 text-sm text-slate-500 text-center">
                      Aucun produit trouvé
                    </div>
                  ) : (
                    filteredProducts.slice(0, 10).map((product) => (
                      <div
                        key={product.id}
                        onClick={() => handleSelectProduct(product)}
                        className="px-3 py-2 hover:bg-slate-100 cursor-pointer border-b border-slate-100 last:border-b-0"
                      >
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-medium text-slate-900">{product.name}</p>
                            {product.sku && (
                              <p className="text-xs text-slate-500">SKU: {product.sku}</p>
                            )}
                          </div>
                          <span className={`text-sm font-semibold ${product.stock <= 5 ? 'text-red-600' : 'text-teal-600'}`}>
                            Stock: {product.stock}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
              
              {/* Produit sélectionné */}
              {selectedProduct && (
                <div className="mt-2 p-2 bg-teal-50 border border-teal-200 rounded-lg flex justify-between items-center">
                  <div>
                    <p className="font-medium text-teal-800">{selectedProduct.name}</p>
                    <p className="text-xs text-teal-600">Stock disponible: {selectedProduct.stock}</p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setSelectedProduct(null);
                      setProductSearch('');
                      setDeclareForm({...declareForm, productId: ''});
                    }}
                    className="text-teal-700 hover:text-teal-900 hover:bg-teal-100"
                  >
                    <XCircle className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
            
            {/* Quantité */}
            <div>
              <Label>Quantité perdue <span className="text-red-500">*</span></Label>
              <Input
                type="number"
                min="1"
                value={declareForm.quantity}
                onChange={(e) => setDeclareForm({...declareForm, quantity: e.target.value})}
                placeholder="Nombre d'unités"
                className="mt-1"
                data-testid="loss-quantity-input"
              />
            </div>
            
            {/* Motif */}
            <div>
              <Label>Motif <span className="text-red-500">*</span></Label>
              <Select 
                value={declareForm.reason} 
                onValueChange={(v) => setDeclareForm({...declareForm, reason: v})}
              >
                <SelectTrigger className="mt-1" data-testid="loss-reason-select">
                  <SelectValue placeholder="Sélectionner un motif" />
                </SelectTrigger>
                <SelectContent>
                  {lossReasons.map((reason) => (
                    <SelectItem key={reason.id} value={reason.id}>
                      {getReasonIcon(reason.id)}
                      {reason.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            {/* Détails */}
            <div>
              <Label>Détails / Explication <span className="text-red-500">*</span></Label>
              <Input
                value={declareForm.reasonDetails}
                onChange={(e) => setDeclareForm({...declareForm, reasonDetails: e.target.value})}
                placeholder="Ex: Boîte tombée, produit périmé..."
                className={`mt-1 ${!declareForm.reasonDetails?.trim() && declareForm.reason ? 'border-red-300' : ''}`}
                required
              />
              {!declareForm.reasonDetails?.trim() && declareForm.reason && (
                <p className="text-xs text-red-500 mt-1">Une explication est requise</p>
              )}
            </div>
            
            {/* Notes */}
            <div>
              <Label>Notes additionnelles</Label>
              <Input
                value={declareForm.notes}
                onChange={(e) => setDeclareForm({...declareForm, notes: e.target.value})}
                placeholder="Informations complémentaires"
                className="mt-1"
              />
            </div>
            
            {/* Info */}
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs text-amber-700">
                <AlertTriangle className="w-3 h-3 inline mr-1" />
                Cette déclaration sera soumise à validation par un administrateur avant d&apos;être appliquée au stock.
              </p>
            </div>
            
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDeclareDialog(false)}>
                Annuler
              </Button>
              <Button 
                type="submit" 
                className="bg-red-600 hover:bg-red-700"
                disabled={declareLoss.isPending || !isFormValid}
                data-testid="submit-loss-btn"
              >
                {declareLoss.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                Déclarer la perte
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      
      {/* Dialog: Rejeter une perte */}
      <Dialog open={showRejectDialog} onOpenChange={setShowRejectDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <XCircle className="w-5 h-5" />
              Rejeter la déclaration
            </DialogTitle>
          </DialogHeader>
          
          {selectedLoss && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-50 rounded-lg">
                <p className="text-sm"><strong>Produit:</strong> {selectedLoss.product_name}</p>
                <p className="text-sm"><strong>Quantité:</strong> {selectedLoss.quantity}</p>
                <p className="text-sm"><strong>Motif:</strong> {selectedLoss.reason_label}</p>
              </div>
              
              <div>
                <Label>Raison du rejet <span className="text-red-500">*</span></Label>
                <Input
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Expliquez pourquoi cette déclaration est rejetée"
                  className="mt-1"
                />
              </div>
              
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowRejectDialog(false)}>
                  Annuler
                </Button>
                <Button 
                  onClick={handleReject}
                  className="bg-red-600 hover:bg-red-700"
                  disabled={validateLoss.isPending}
                >
                  {validateLoss.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Confirmer le rejet
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default StockLosses;
