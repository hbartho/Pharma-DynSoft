import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Progress } from '../components/ui/progress';
import { 
  Wallet, Search, Users, AlertTriangle, TrendingUp, 
  CreditCard, Banknote, DollarSign, Clock, CheckCircle2,
  ArrowDownCircle, History, Eye, ChevronRight, Smartphone,
  FileCheck, Loader2, AlertCircle, RefreshCw, Calendar,
  Shield, Send, CheckCircle, X, CircleDollarSign, XCircle, Trash2
} from 'lucide-react';
import { toast } from 'sonner';
import { useSettings } from '../contexts/SettingsContext';
import { 
  useDebtDashboard, 
  useCustomersDebtSummary, 
  useCustomerDebts,
  useCreateDebtPayment,
  useCreateBulkPayment,
  useWriteOffDebt,
  usePaymentsHistory 
} from '../hooks/useDebts';
import { useDebtsInfinite } from '../hooks/useInfiniteScroll';
import { usePaymentMethods } from '../hooks/usePaymentMethods';
import { useSettingsQuery } from '../hooks/useSettings';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { SkeletonTable, SkeletonStatsCard } from '../components/ui/skeleton-shimmer';
import { useAuth } from '../contexts/AuthContext';

const Debts = () => {
  const { formatAmount } = useSettings();
  const loadMoreRef = useRef(null);
  
  // Récupérer l'utilisateur courant pour vérifier le rôle
  const { user } = useAuth();
  const isAdminUser = user?.role === 'admin';
  
  // Vérifier si un shift est ouvert (requis pour les opérations financières)
  // Les admins sont exemptés de cette exigence
  const { data: currentShift } = useCurrentShift();
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // États
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('active'); // active = pending + partial
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState('all'); // Filtre par période
  
  // États pour l'abandon de dette
  const [showWriteOffDialog, setShowWriteOffDialog] = useState(false);
  const [selectedDebtForWriteOff, setSelectedDebtForWriteOff] = useState(null);
  const [writeOffReason, setWriteOffReason] = useState('');
  
  // États pour les filtres de l'historique
  const [historyFilters, setHistoryFilters] = useState({
    customerId: '',
    paymentMethod: '',
    dateFrom: '',
    dateTo: '',
  });
  
  // État du formulaire de paiement
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    paymentMethod: 'cash',
    notes: '',
  });
  
  // États pour les détails de paiement selon le mode
  const [paymentDetails, setPaymentDetails] = useState({
    orange_sender_number: '',
    orange_ticket_ref: '',
    mtn_sender_number: '',
    mtn_ticket_ref: '',
    check_holder_name: '',
    check_number: '',
    check_bank: '',
    card_holder_name: '',
    card_last_digits: '',
    card_bank: '',
  });
  
  // États pour OTP (Mobile Money)
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);
  
  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Queries avec infinite scroll pour les dettes
  const { 
    data: debtsData,
    isLoading: debtsInfiniteLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage 
  } = useDebtsInfinite({
    limit: 20,
    search: debouncedSearch,
    status: filterStatus === 'all' ? '' : filterStatus
  });
  
  const debts = debtsData?.pages?.flatMap(page => page.items) || [];
  const totalDebts = debtsData?.pages?.[0]?.total || 0;
  
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
  
  // Queries existantes
  const { data: dashboardStats, isLoading: dashboardLoading, refetch: refetchDashboard } = useDebtDashboard(selectedPeriod);
  const { data: customersSummary = [], isLoading: customersLoading, refetch: refetchCustomers } = useCustomersDebtSummary(true);
  const { data: selectedCustomerDebts = [], isLoading: debtsLoading, refetch: refetchCustomerDebts } = useCustomerDebts(selectedCustomer?.customer_id, true);
  const { data: paymentsHistory = [], isLoading: historyLoading, refetch: refetchHistory } = usePaymentsHistory({
    customerId: historyFilters.customerId || undefined,
    paymentMethod: historyFilters.paymentMethod || undefined,
    dateFrom: historyFilters.dateFrom || undefined,
    dateTo: historyFilters.dateTo || undefined,
    limit: 50,
  });
  const { data: paymentMethods = [] } = usePaymentMethods(true);
  const { data: settings } = useSettingsQuery();
  
  // Fonction pour rafraîchir toutes les données
  const refreshAllData = () => {
    refetchDashboard();
    refetchCustomers();
    refetchHistory();
  };
  
  // Options de période
  const periodOptions = [
    { value: 'all', label: 'Tout', icon: '📊' },
    { value: 'week', label: 'Cette semaine', icon: '📅' },
    { value: 'month', label: 'Ce mois', icon: '🗓️' },
    { value: 'quarter', label: 'Ce trimestre', icon: '📆' },
    { value: 'year', label: 'Cette année', icon: '🗃️' },
  ];
  
  // Nombre de clients à afficher dans le Top (configurable dans les paramètres)
  const topDebtCustomersCount = settings?.top_debt_customers_count || 10;
  
  // Mutations
  const createBulkPayment = useCreateBulkPayment();
  const writeOffDebt = useWriteOffDebt();
  
  // Filtrer les méthodes de paiement (exclure "debt" pour les remboursements)
  const availablePaymentMethods = paymentMethods.filter(m => m.code !== 'debt');
  
  // Vérifie si le mode de paiement actuel est Mobile Money
  const isMobileMoneyPayment = paymentForm.paymentMethod === 'orange_money' || paymentForm.paymentMethod === 'mtn_money';
  
  // Obtenir le numéro OTP par défaut des paramètres (pour l'envoi du code OTP)
  const getDefaultOtpPhone = () => {
    if (paymentForm.paymentMethod === 'orange_money' && settings?.orange_money_default_phone) {
      return settings.orange_money_default_phone;
    }
    if (paymentForm.paymentMethod === 'mtn_money' && settings?.mtn_money_default_phone) {
      return settings.mtn_money_default_phone;
    }
    return '';
  };
  
  // Réinitialiser l'état OTP
  const resetOtpState = () => {
    setOtpCode('');
    setOtpSent(false);
    setOtpVerified(false);
    setOtpLoading(false);
    setOtpError('');
    setOtpCountdown(0);
  };
  
  // Réinitialiser les détails de paiement
  const resetPaymentDetails = () => {
    setPaymentDetails({
      orange_sender_number: '',
      orange_ticket_ref: '',
      mtn_sender_number: '',
      mtn_ticket_ref: '',
      check_holder_name: '',
      check_number: '',
      check_bank: '',
      card_holder_name: '',
      card_last_digits: '',
      card_bank: '',
    });
  };
  
  // Effet pour le compte à rebours OTP
  useEffect(() => {
    if (otpCountdown > 0) {
      const timer = setTimeout(() => setOtpCountdown(otpCountdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpCountdown]);
  
  // Reset OTP state when payment method changes
  useEffect(() => {
    resetOtpState();
  }, [paymentForm.paymentMethod]);
  
  // Demander un code OTP (simulation)
  const handleRequestOtp = async () => {
    const otpTargetNumber = getDefaultOtpPhone();
    
    if (!otpTargetNumber) {
      setOtpError('Aucun numéro OTP configuré dans les paramètres');
      return;
    }
    
    setOtpLoading(true);
    setOtpError('');
    
    try {
      // Simulation d'envoi OTP - délai de 1.5s
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setOtpSent(true);
      setOtpCountdown(60);
      toast.success(`Code OTP envoyé au ${otpTargetNumber}`, {
        description: 'Pour la démo, utilisez le code: 123456'
      });
    } catch (error) {
      setOtpError('Erreur lors de l\'envoi du code OTP');
      toast.error('Échec de l\'envoi du code OTP');
    } finally {
      setOtpLoading(false);
    }
  };
  
  // Vérifier le code OTP (simulation)
  const handleVerifyOtp = async () => {
    if (!otpCode || otpCode.length < 4) {
      setOtpError('Veuillez saisir le code OTP complet');
      return;
    }
    
    setOtpLoading(true);
    setOtpError('');
    
    try {
      // Simulation de vérification - délai de 1s
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Pour la démo, accepter "123456" comme code valide
      if (otpCode === '123456') {
        setOtpVerified(true);
        setOtpError('');
        toast.success('Code OTP validé avec succès!');
      } else {
        setOtpError('Code OTP incorrect. Pour la démo, utilisez: 123456');
        toast.error('Code OTP incorrect');
      }
    } catch (error) {
      setOtpError('Erreur lors de la vérification du code');
    } finally {
      setOtpLoading(false);
    }
  };
  
  // Filtrer les clients par recherche et trier par dette (plus endettés en premier)
  const filteredCustomers = customersSummary
    .filter(c => 
      c.customer_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.customer_phone?.includes(searchQuery)
    )
    .sort((a, b) => (b.total_debt || 0) - (a.total_debt || 0));
  
  // Top clients les plus endettés (pour le dashboard) - nombre configurable
  // Exclure les clients avec dette < 1 GNF (pour éviter les erreurs d'arrondi)
  const topDebtCustomers = [...customersSummary]
    .filter(c => c.total_debt >= 1)
    .sort((a, b) => b.total_debt - a.total_debt)
    .slice(0, topDebtCustomersCount);
  
  // Ouvrir le dialog de détail client
  const handleViewCustomer = (customer) => {
    setSelectedCustomer(customer);
    setShowDetailDialog(true);
  };
  
  // Ouvrir le dialog de paiement
  const handleOpenPayment = (customer) => {
    setSelectedCustomer(customer);
    setPaymentForm({
      amount: Math.round(customer.total_debt).toString(),
      paymentMethod: 'cash',
      notes: '',
    });
    resetPaymentDetails();
    resetOtpState();
    setShowPaymentDialog(true);
  };
  
  // Soumettre le paiement
  const handleSubmitPayment = async (e) => {
    e.preventDefault();
    
    const amount = parseFloat(paymentForm.amount);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Veuillez saisir un montant valide');
      return;
    }
    
    if (amount > selectedCustomer.total_debt) {
      toast.error('Le montant ne peut pas dépasser la dette totale');
      return;
    }
    
    // Validation OTP obligatoire pour Mobile Money
    if (isMobileMoneyPayment && !otpVerified) {
      toast.error('Veuillez valider le code OTP pour finaliser le paiement Mobile Money');
      return;
    }
    
    // Préparer les détails de paiement selon le mode
    let paymentDetailsData = null;
    const selectedMethod = availablePaymentMethods.find(m => m.code === paymentForm.paymentMethod);
    
    if (selectedMethod && selectedMethod.required_fields && selectedMethod.required_fields.length > 0) {
      paymentDetailsData = {};
      for (const field of selectedMethod.required_fields) {
        const fieldKey = `${paymentForm.paymentMethod}_${field.name}`;
        paymentDetailsData[field.name] = paymentDetails[fieldKey] || '';
      }
    }
    
    createBulkPayment.mutate(
      {
        customerId: selectedCustomer.customer_id,
        amount: amount,
        paymentMethod: paymentForm.paymentMethod,
        paymentDetails: paymentDetailsData,
        notes: paymentForm.notes,
      },
      {
        onSuccess: (data) => {
          toast.success(`Remboursement de ${formatAmount(data.total_applied)} enregistré`);
          setShowPaymentDialog(false);
          setSelectedCustomer(null);
          resetPaymentDetails();
          resetOtpState();
          refreshAllData();
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors du remboursement');
        },
      }
    );
  };
  
  // Ouvrir le modal d'abandon de dette
  const handleOpenWriteOff = (customer) => {
    setSelectedDebtForWriteOff(customer);
    setWriteOffReason('');
    setShowWriteOffDialog(true);
  };
  
  // Soumettre l'abandon de dette
  const handleSubmitWriteOff = async (e) => {
    e.preventDefault();
    
    if (!writeOffReason.trim()) {
      toast.error('Veuillez saisir une raison pour l\'abandon');
      return;
    }
    
    // On récupère les dettes du client pour les abandonner une par une
    // ou on peut créer un endpoint bulk write-off côté backend
    // Pour simplifier, on va d'abord récupérer les dettes actives du client
    try {
      // Abandonner chaque dette active du client
      const debtsToWriteOff = selectedCustomerDebts.filter(d => d.status !== 'paid' && d.status !== 'abandoned');
      
      if (debtsToWriteOff.length === 0) {
        toast.error('Aucune dette active à abandonner');
        return;
      }
      
      // Abandonner toutes les dettes
      for (const debt of debtsToWriteOff) {
        await writeOffDebt.mutateAsync({
          debtId: debt.id,
          reason: writeOffReason
        });
      }
      
      toast.success(`${debtsToWriteOff.length} dette(s) abandonnée(s) avec succès`);
      setShowWriteOffDialog(false);
      setSelectedDebtForWriteOff(null);
      setWriteOffReason('');
      refreshAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'abandon');
    }
  };
  
  // Obtenir l'icône du mode de paiement
  const getPaymentIcon = (method) => {
    switch (method) {
      case 'card': return <CreditCard className="w-4 h-4" />;
      case 'orange_money':
      case 'mtn_money': return <Smartphone className="w-4 h-4" />;
      case 'check': return <FileCheck className="w-4 h-4" />;
      case 'write_off': return <XCircle className="w-4 h-4" />;
      default: return <Banknote className="w-4 h-4" />;
    }
  };
  
  // Formater les détails de paiement pour l'affichage dans l'historique
  const formatPaymentDetails = (method, details) => {
    if (!details) return null;
    
    const elements = [];
    
    switch (method) {
      case 'orange_money':
      case 'mtn_money':
        if (details.sender_number) {
          elements.push(
            <span key="phone" className="inline-flex items-center gap-1">
              <Smartphone className="w-3 h-3" />
              {details.sender_number}
            </span>
          );
        }
        if (details.ticket_ref) {
          elements.push(
            <span key="ref" className="text-slate-400">
              Réf: {details.ticket_ref}
            </span>
          );
        }
        break;
        
      case 'card':
        if (details.holder_name) {
          elements.push(
            <span key="holder" className="inline-flex items-center gap-1">
              <CreditCard className="w-3 h-3" />
              {details.holder_name}
            </span>
          );
        }
        if (details.last_digits) {
          elements.push(
            <span key="digits" className="text-slate-400">
              **** {details.last_digits}
            </span>
          );
        }
        if (details.bank) {
          elements.push(
            <span key="bank" className="text-slate-400">
              {details.bank}
            </span>
          );
        }
        break;
        
      case 'check':
        if (details.holder_name) {
          elements.push(
            <span key="holder" className="inline-flex items-center gap-1">
              <FileCheck className="w-3 h-3" />
              {details.holder_name}
            </span>
          );
        }
        if (details.check_number) {
          elements.push(
            <span key="number" className="text-slate-400">
              N° {details.check_number}
            </span>
          );
        }
        if (details.bank) {
          elements.push(
            <span key="bank" className="text-slate-400">
              {details.bank}
            </span>
          );
        }
        break;
        
      default:
        // Pour les autres modes, afficher toutes les valeurs non vides
        Object.entries(details).forEach(([key, value]) => {
          if (value) {
            elements.push(
              <span key={key} className="text-slate-400">
                {value}
              </span>
            );
          }
        });
    }
    
    return elements.length > 0 ? (
      <div className="flex flex-wrap gap-x-2 gap-y-0.5 justify-center">
        {elements}
      </div>
    ) : null;
  };
  
  // Formater la date
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };
  
  // Calculer le pourcentage d'utilisation du crédit
  const getCreditUsagePercent = (totalDebt, maxLimit) => {
    if (!maxLimit || maxLimit === 0) return 0;
    return Math.min(100, Math.round((totalDebt / maxLimit) * 100));
  };
  
  // Obtenir la couleur selon le pourcentage
  const getUsageColor = (percent) => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= 70) return 'bg-orange-500';
    if (percent >= 50) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="debts-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-4xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Gestion des Dettes
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Suivez et gérez les créances clients
            </p>
          </div>
          <Button 
            onClick={() => refreshAllData()}
            variant="outline"
            size="sm"
            className="rounded-full"
          >
            <RefreshCw className="w-4 h-4 sm:mr-2" />
            <span className="hidden sm:inline">Actualiser</span>
          </Button>
        </div>
        
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          {/* Tabs responsive - scroll horizontal sur mobile */}
          <TabsList className="bg-slate-100 p-1 sm:p-1.5 rounded-full gap-1 w-full overflow-x-auto flex-nowrap">
            <TabsTrigger 
              value="dashboard" 
              className={`rounded-full px-3 sm:px-6 py-2 sm:py-2.5 transition-all duration-200 text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'dashboard' 
                  ? 'bg-teal-600 text-white shadow-md data-[state=active]:bg-teal-600 data-[state=active]:text-white' 
                  : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4 sm:mr-2" />
              <span className="hidden sm:inline">Tableau de bord</span>
              <span className="sm:hidden ml-1">Dashboard</span>
            </TabsTrigger>
            <TabsTrigger 
              value="customers" 
              className={`rounded-full px-3 sm:px-6 py-2 sm:py-2.5 transition-all duration-200 text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'customers' 
                  ? 'bg-teal-600 text-white shadow-md data-[state=active]:bg-teal-600 data-[state=active]:text-white' 
                  : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              <Users className="w-3 h-3 sm:w-4 sm:h-4 sm:mr-2" />
              <span className="hidden sm:inline">Clients endettés</span>
              <span className="sm:hidden ml-1">Clients</span>
            </TabsTrigger>
            <TabsTrigger 
              value="history" 
              className={`rounded-full px-3 sm:px-6 py-2 sm:py-2.5 transition-all duration-200 text-xs sm:text-sm whitespace-nowrap ${
                activeTab === 'history' 
                  ? 'bg-teal-600 text-white shadow-md data-[state=active]:bg-teal-600 data-[state=active]:text-white' 
                  : 'text-slate-600 hover:bg-slate-200'
              }`}
            >
              <History className="w-3 h-3 sm:w-4 sm:h-4 sm:mr-2" />
              <span className="hidden sm:inline">Historique</span>
              <span className="sm:hidden ml-1">Hist.</span>
            </TabsTrigger>
          </TabsList>
          
          {/* Avertissement si pas de shift ouvert */}
          {!canOperate && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
              <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-800">Aucun shift ouvert</p>
                <p className="text-xs text-amber-600">
                  Vous devez ouvrir un shift pour encaisser des remboursements ou abandonner des dettes.
                </p>
              </div>
            </div>
          )}
          
          {/* TAB: Dashboard */}
          <TabsContent value="dashboard" className="space-y-6 mt-6">
            {/* Filtre par période - responsive */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex flex-wrap items-center gap-2">
                <Calendar className="w-4 h-4 sm:w-5 sm:h-5 text-slate-400" />
                <span className="text-xs sm:text-sm font-medium text-slate-700">Période :</span>
                <div className="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-full">
                  {periodOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => setSelectedPeriod(option.value)}
                      className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-200 ${
                        selectedPeriod === option.value
                          ? 'bg-white text-teal-700 shadow-sm'
                          : 'text-slate-600 hover:text-slate-900'
                      }`}
                    >
                      <span className="hidden sm:inline">{option.label}</span>
                      <span className="sm:hidden">{option.value === 'all' ? 'Tout' : option.value === 'today' ? 'Jour' : option.value === 'week' ? 'Sem.' : option.value === 'month' ? 'Mois' : option.value === 'quarter' ? 'Trim.' : 'An'}</span>
                    </button>
                  ))}
                </div>
              </div>
              {dashboardStats?.period_label && selectedPeriod !== 'all' && (
                <span className="text-xs sm:text-sm text-slate-500">
                  Affichage : {dashboardStats.period_label}
                </span>
              )}
            </div>
            
            {/* Stats Cards */}
            {dashboardLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[1, 2, 3, 4].map(i => <SkeletonStatsCard key={i} />)}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Total Créances */}
                <div className="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-2xl border border-red-200">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-red-700">Total Créances</span>
                    <div className="p-2 bg-red-200 rounded-xl">
                      <Wallet className="w-5 h-5 text-red-700" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-red-900">
                    {formatAmount(dashboardStats?.total_receivables || 0)}
                  </p>
                  <p className="text-sm text-red-600 mt-1">
                    {dashboardStats?.total_debts_count || 0} dettes en cours
                  </p>
                </div>
                
                {/* Clients Endettés */}
                <div className="bg-gradient-to-br from-orange-50 to-orange-100 p-6 rounded-2xl border border-orange-200">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-orange-700">Clients Endettés</span>
                    <div className="p-2 bg-orange-200 rounded-xl">
                      <Users className="w-5 h-5 text-orange-700" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-orange-900">
                    {dashboardStats?.total_customers_with_debt || 0}
                  </p>
                  <p className="text-sm text-orange-600 mt-1">
                    Moy: {formatAmount(dashboardStats?.average_debt_per_customer || 0)}
                  </p>
                </div>
                
                {/* En Retard */}
                <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 p-6 rounded-2xl border border-yellow-200">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-yellow-700">En Retard</span>
                    <div className="p-2 bg-yellow-200 rounded-xl">
                      <AlertTriangle className="w-5 h-5 text-yellow-700" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-yellow-900">
                    {formatAmount(dashboardStats?.overdue_amount || 0)}
                  </p>
                  <p className="text-sm text-yellow-600 mt-1">
                    {dashboardStats?.overdue_count || 0} dettes en retard
                  </p>
                </div>
                
                {/* Encaissé (période) */}
                <div className="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-2xl border border-green-200">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-medium text-green-700">
                      Encaissé {selectedPeriod === 'all' ? 'ce mois' : dashboardStats?.period_label || ''}
                    </span>
                    <div className="p-2 bg-green-200 rounded-xl">
                      <ArrowDownCircle className="w-5 h-5 text-green-700" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-green-900">
                    {formatAmount(dashboardStats?.collected_this_period || 0)}
                  </p>
                  <p className="text-sm text-green-600 mt-1">
                    Remboursements reçus
                  </p>
                </div>
              </div>
            )}
            
            {/* Top 5 Clients avec Dettes */}
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-slate-900">Top Clients Endettés</h3>
                  <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                    {topDebtCustomers.length} clients
                  </span>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setActiveTab('customers')}
                >
                  Voir tout
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </div>
              {customersLoading ? (
                <SkeletonTable rows={5} columns={4} />
              ) : (
                <div className="divide-y divide-slate-100">
                  {topDebtCustomers.map((customer, index) => {
                    const usagePercent = getCreditUsagePercent(customer.total_debt, customer.max_debt_limit);
                    return (
                      <div 
                        key={customer.customer_id} 
                        className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
                      >
                        {/* Rang */}
                        <div className="flex items-center gap-4">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === 0 ? 'bg-red-100 text-red-700' :
                            index === 1 ? 'bg-orange-100 text-orange-700' :
                            index === 2 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {index + 1}
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center">
                              <span className="text-sm font-medium text-slate-600">
                                {customer.customer_name?.charAt(0)?.toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-slate-900">{customer.customer_name}</p>
                                {customer.has_overdue && (
                                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200">
                                    <AlertTriangle className="w-3 h-3" />
                                    En retard
                                  </span>
                                )}
                              </div>
                              <p className="text-sm text-slate-500">{customer.customer_phone}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-6">
                          <div className="text-right">
                            <p className="font-semibold text-red-600">{formatAmount(customer.total_debt)}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <Progress value={usagePercent} className="w-20 h-2" />
                              <span className="text-xs text-slate-500">{usagePercent}%</span>
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              onClick={() => handleOpenPayment(customer)}
                              className="bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                              disabled={!canOperate}
                              title={!canOperate ? shiftBlockReason : ""}
                            >
                              <DollarSign className="w-4 h-4 mr-1" />
                              Encaisser
                            </Button>
                            {isAdminUser && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedCustomer(customer);
                                  handleOpenWriteOff(customer);
                                }}
                                className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={!canOperate}
                                title={!canOperate ? shiftBlockReason : ""}
                                data-testid="write-off-btn-dashboard"
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Abandonner
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {topDebtCustomers.length === 0 && (
                    <div className="text-center py-12">
                      <CheckCircle2 className="w-12 h-12 text-green-300 mx-auto mb-3" />
                      <p className="text-slate-500">Aucun client endetté</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </TabsContent>
          
          {/* TAB: Clients Endettés */}
          <TabsContent value="customers" className="space-y-6 mt-6">
            {/* Recherche */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                placeholder="Rechercher un client par nom ou téléphone..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 rounded-full"
              />
            </div>
            
            {/* Liste des clients */}
            {customersLoading ? (
              <SkeletonTable rows={8} columns={6} />
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Client</th>
                      <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900">Dette Actuelle</th>
                      <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900">Seuil Max</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Utilisation</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Nb Dettes</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {filteredCustomers.map((customer) => {
                      const usagePercent = getCreditUsagePercent(customer.total_debt, customer.max_debt_limit);
                      return (
                        <tr key={customer.customer_id} className="hover:bg-slate-50 transition-colors">
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 bg-slate-200 rounded-full flex items-center justify-center">
                                <span className="text-sm font-medium text-slate-600">
                                  {customer.customer_name?.charAt(0)?.toUpperCase()}
                                </span>
                              </div>
                              <div>
                                <p className="font-medium text-slate-900">{customer.customer_name}</p>
                                <p className="text-sm text-slate-500">{customer.customer_phone}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <span className="font-semibold text-red-600">{formatAmount(customer.total_debt)}</span>
                          </td>
                          <td className="px-6 py-4 text-right">
                            <span className="text-slate-700">{formatAmount(customer.max_debt_limit)}</span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-center gap-2">
                              <Progress 
                                value={usagePercent} 
                                className={`w-24 h-2 ${getUsageColor(usagePercent)}`} 
                              />
                              <span className={`text-sm font-medium ${usagePercent >= 90 ? 'text-red-600' : 'text-slate-600'}`}>
                                {usagePercent}%
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-center">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700">
                              {customer.debts_count}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center justify-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleViewCustomer(customer)}
                              >
                                <Eye className="w-4 h-4" />
                              </Button>
                              <Button
                                size="sm"
                                onClick={() => handleOpenPayment(customer)}
                                className="bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                disabled={!canOperate}
                                title={!canOperate ? shiftBlockReason : ""}
                              >
                                <DollarSign className="w-4 h-4 mr-1" />
                                Encaisser
                              </Button>
                              {isAdminUser && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setSelectedCustomer(customer);
                                    handleOpenWriteOff(customer);
                                  }}
                                  className="text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300 disabled:opacity-50 disabled:cursor-not-allowed"
                                  disabled={!canOperate}
                                  title={!canOperate ? shiftBlockReason : ""}
                                  data-testid="write-off-btn-table"
                                >
                                  <XCircle className="w-4 h-4 mr-1" />
                                  Abandonner
                                </Button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                
                {/* Infinite Scroll Info pour les clients */}
                {filteredCustomers.length > 0 && (
                  <div className="flex flex-col items-center gap-3 py-4 border-t border-slate-100">
                    <p className="text-sm text-slate-500">
                      {filteredCustomers.length} client{filteredCustomers.length > 1 ? 's' : ''} avec dette{filteredCustomers.length > 1 ? 's' : ''}
                    </p>
                  </div>
                )}
                
                {filteredCustomers.length === 0 && (
                  <div className="text-center py-12">
                    <CheckCircle2 className="w-12 h-12 text-green-300 mx-auto mb-3" />
                    <p className="text-slate-500">Aucun client endetté trouvé</p>
                  </div>
                )}
              </div>
            )}
          </TabsContent>
          
          {/* TAB: Historique */}
          <TabsContent value="history" className="space-y-6 mt-6">
            {/* Filtres avancés */}
            <div className="bg-white rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-4">
                <Search className="w-5 h-5 text-slate-400" />
                <h3 className="font-medium text-slate-700">Filtrer les remboursements</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                {/* Filtre par client */}
                <div>
                  <Label className="text-xs text-slate-500 mb-1 block">Client</Label>
                  <Select 
                    value={historyFilters.customerId || 'all'} 
                    onValueChange={(v) => setHistoryFilters({...historyFilters, customerId: v === 'all' ? '' : v})}
                  >
                    <SelectTrigger className="h-9" data-testid="history-filter-customer">
                      <SelectValue placeholder="Tous les clients" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les clients</SelectItem>
                      {customersSummary.map((customer) => (
                        <SelectItem key={customer.customer_id} value={customer.customer_id}>
                          {customer.customer_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Filtre par mode de paiement */}
                <div>
                  <Label className="text-xs text-slate-500 mb-1 block">Mode de paiement</Label>
                  <Select 
                    value={historyFilters.paymentMethod || 'all'} 
                    onValueChange={(v) => setHistoryFilters({...historyFilters, paymentMethod: v === 'all' ? '' : v})}
                  >
                    <SelectTrigger className="h-9" data-testid="history-filter-method">
                      <SelectValue placeholder="Tous les modes" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous les modes</SelectItem>
                      {availablePaymentMethods.map((method) => (
                        <SelectItem key={method.code} value={method.code}>
                          <div className="flex items-center gap-2">
                            {getPaymentIcon(method.code)}
                            {method.name}
                          </div>
                        </SelectItem>
                      ))}
                      {/* Option pour les passages en perte */}
                      <SelectItem value="write_off">
                        <div className="flex items-center gap-2 text-red-600">
                          <XCircle className="w-4 h-4" />
                          Passages en perte
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                
                {/* Date de début */}
                <div>
                  <Label className="text-xs text-slate-500 mb-1 block">Date début</Label>
                  <Input
                    type="date"
                    value={historyFilters.dateFrom}
                    onChange={(e) => setHistoryFilters({...historyFilters, dateFrom: e.target.value})}
                    className="h-9"
                    data-testid="history-filter-date-from"
                  />
                </div>
                
                {/* Date de fin */}
                <div>
                  <Label className="text-xs text-slate-500 mb-1 block">Date fin</Label>
                  <Input
                    type="date"
                    value={historyFilters.dateTo}
                    onChange={(e) => setHistoryFilters({...historyFilters, dateTo: e.target.value})}
                    className="h-9"
                    data-testid="history-filter-date-to"
                  />
                </div>
                
                {/* Bouton réinitialiser */}
                <div className="flex items-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setHistoryFilters({ customerId: '', paymentMethod: '', dateFrom: '', dateTo: '' })}
                    className="h-9 w-full"
                    data-testid="history-filter-reset"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Réinitialiser
                  </Button>
                </div>
              </div>
              
              {/* Badge avec nombre de résultats */}
              <div className="mt-3 flex items-center gap-2">
                <span className="text-sm text-slate-500">
                  {paymentsHistory.length} remboursement{paymentsHistory.length > 1 ? 's' : ''} trouvé{paymentsHistory.length > 1 ? 's' : ''}
                </span>
                {(historyFilters.customerId || historyFilters.paymentMethod || historyFilters.dateFrom || historyFilters.dateTo) && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-teal-100 text-teal-700">
                    Filtres actifs
                  </span>
                )}
              </div>
            </div>
            
            {historyLoading ? (
              <SkeletonTable rows={10} columns={5} />
            ) : (
              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-200">
                  <h3 className="font-semibold text-slate-900">Derniers Remboursements</h3>
                </div>
                <table className="w-full">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Date</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Client</th>
                      <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900">Montant</th>
                      <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900">Mode & Détails</th>
                      <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900">Par</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {paymentsHistory.map((payment) => {
                      const isWriteOff = payment.payment_method === 'write_off' || payment.transaction_type === 'write_off';
                      return (
                        <tr 
                          key={payment.id} 
                          className={`transition-colors ${isWriteOff ? 'bg-red-50 hover:bg-red-100' : 'hover:bg-slate-50'}`}
                        >
                          <td className="px-6 py-4 text-slate-600">
                            {formatDate(payment.created_at)}
                          </td>
                          <td className="px-6 py-4 font-medium text-slate-900">
                            {payment.customer_name}
                          </td>
                          <td className="px-6 py-4 text-right">
                            <span className={`font-semibold ${isWriteOff ? 'text-red-600' : 'text-green-600'}`}>
                              {isWriteOff ? '-' : '+'}{formatAmount(payment.amount)}
                            </span>
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex flex-col items-center gap-1">
                              <div className="flex items-center gap-2">
                                {getPaymentIcon(payment.payment_method)}
                                <span className={`text-sm font-medium ${isWriteOff ? 'text-red-700' : 'text-slate-700'}`}>
                                  {isWriteOff 
                                    ? 'Passage en perte' 
                                    : (availablePaymentMethods.find(m => m.code === payment.payment_method)?.name || payment.payment_method)
                                  }
                                </span>
                              </div>
                              {/* Affichage de la raison d'abandon ou des détails de paiement */}
                              {isWriteOff && payment.notes && (
                                <div className="text-xs text-red-600 italic">
                                  {payment.notes}
                                </div>
                              )}
                              {!isWriteOff && payment.payment_details && Object.keys(payment.payment_details).length > 0 && (
                                <div className="text-xs text-slate-500 space-y-0.5">
                                  {formatPaymentDetails(payment.payment_method, payment.payment_details)}
                                </div>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 text-slate-600">
                            {payment.created_by_name || '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                
                {paymentsHistory.length === 0 && (
                  <div className="text-center py-12">
                    <History className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                    <p className="text-slate-500">Aucun remboursement enregistré</p>
                  </div>
                )}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
      
      {/* Dialog de Paiement */}
      <Dialog open={showPaymentDialog} onOpenChange={setShowPaymentDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Enregistrer un Remboursement
            </DialogTitle>
          </DialogHeader>
          
          {selectedCustomer && (
            <form onSubmit={handleSubmitPayment} className="space-y-4">
              {/* Info Client */}
              <div className="p-4 bg-slate-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-slate-200 rounded-full flex items-center justify-center">
                    <span className="text-lg font-medium text-slate-600">
                      {selectedCustomer.customer_name?.charAt(0)?.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{selectedCustomer.customer_name}</p>
                    <p className="text-sm text-red-600">
                      Dette: {formatAmount(selectedCustomer.total_debt)}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Montant */}
              <div>
                <Label htmlFor="amount">Montant du remboursement <span className="text-red-500">*</span></Label>
                <div className="relative mt-1">
                  <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
                  <Input
                    id="amount"
                    type="number"
                    step="0.01"
                    max={selectedCustomer.total_debt}
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
                    placeholder="0.00"
                    className="pl-10"
                  />
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-xs text-slate-500">Max: {formatAmount(selectedCustomer.total_debt)}</span>
                  <button
                    type="button"
                    onClick={() => setPaymentForm({ ...paymentForm, amount: selectedCustomer.total_debt.toString() })}
                    className="text-xs text-teal-600 hover:underline"
                  >
                    Tout rembourser
                  </button>
                </div>
              </div>
              
              {/* Mode de paiement */}
              <div>
                <Label>Mode de paiement</Label>
                <Select 
                  value={paymentForm.paymentMethod} 
                  onValueChange={(v) => {
                    setPaymentForm({ ...paymentForm, paymentMethod: v });
                    resetPaymentDetails();
                  }}
                >
                  <SelectTrigger className="mt-1" data-testid="debt-payment-method-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {availablePaymentMethods.map((method) => (
                      <SelectItem key={method.code} value={method.code}>
                        <div className="flex items-center gap-2">
                          {getPaymentIcon(method.code)}
                          {method.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Champs conditionnels selon le mode de paiement - RENDU DYNAMIQUE */}
              {(() => {
                const selectedMethod = availablePaymentMethods.find(m => m.code === paymentForm.paymentMethod);
                if (!selectedMethod || !selectedMethod.required_fields || selectedMethod.required_fields.length === 0) {
                  return null;
                }
                
                const colorSchemes = {
                  orange: { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-700', label: 'text-orange-800' },
                  blue: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', label: 'text-blue-800' },
                  purple: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', label: 'text-purple-800' },
                  green: { bg: 'bg-green-50', border: 'border-green-200', text: 'text-green-700', label: 'text-green-800' },
                  yellow: { bg: 'bg-yellow-50', border: 'border-yellow-200', text: 'text-yellow-700', label: 'text-yellow-800' },
                  red: { bg: 'bg-red-50', border: 'border-red-200', text: 'text-red-700', label: 'text-red-800' },
                  default: { bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-700', label: 'text-slate-800' },
                };
                
                const colors = colorSchemes[selectedMethod.color] || colorSchemes.default;
                
                return (
                  <div className={`p-3 ${colors.bg} rounded-lg border ${colors.border} space-y-2`}>
                    <div className={`flex items-center gap-2 ${colors.text} text-sm font-medium`}>
                      {getPaymentIcon(selectedMethod.code)}
                      Détails {selectedMethod.name}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {selectedMethod.required_fields.map((field) => (
                        <div key={field.name}>
                          <Label className={`text-xs ${colors.label}`}>
                            {field.label} {field.required && <span className="text-red-500">*</span>}
                          </Label>
                          <Input
                            type={field.type || 'text'}
                            maxLength={field.maxLength}
                            value={paymentDetails[`${paymentForm.paymentMethod}_${field.name}`] || ''}
                            onChange={(e) => {
                              let value = e.target.value;
                              if (field.maxLength && field.type !== 'tel') {
                                value = value.replace(/\D/g, '').slice(0, field.maxLength);
                              }
                              setPaymentDetails({
                                ...paymentDetails,
                                [`${paymentForm.paymentMethod}_${field.name}`]: value
                              });
                            }}
                            placeholder={field.placeholder || ''}
                            className="mt-1 bg-white h-9 text-sm"
                            data-testid={`debt-payment-field-${field.name}`}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
              
              {/* Section OTP pour Mobile Money */}
              {isMobileMoneyPayment && (
                <div className={`p-3 rounded-lg border space-y-3 ${
                  otpVerified 
                    ? 'bg-green-50 border-green-200' 
                    : paymentForm.paymentMethod === 'orange_money' 
                      ? 'bg-orange-50 border-orange-200' 
                      : 'bg-yellow-50 border-yellow-200'
                }`}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Shield className={`w-4 h-4 ${otpVerified ? 'text-green-600' : paymentForm.paymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`} />
                      <span className={`text-sm font-medium ${otpVerified ? 'text-green-700' : paymentForm.paymentMethod === 'orange_money' ? 'text-orange-700' : 'text-yellow-700'}`}>
                        Vérification OTP {otpVerified && '✓ Validé'}
                      </span>
                    </div>
                    {otpVerified && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                        <CheckCircle className="w-3 h-3" />
                        Autorisé
                      </span>
                    )}
                  </div>

                  {!otpVerified && (
                    <div className="space-y-2">
                      {!otpSent ? (
                        <div className="space-y-2">
                          <p className={`text-xs ${paymentForm.paymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`}>
                            Code envoyé au: <strong>{getDefaultOtpPhone() || 'Non configuré'}</strong>
                          </p>
                          <Button
                            type="button"
                            size="sm"
                            onClick={handleRequestOtp}
                            disabled={otpLoading || !getDefaultOtpPhone()}
                            className={`w-full ${
                              paymentForm.paymentMethod === 'orange_money' 
                                ? 'bg-orange-600 hover:bg-orange-700' 
                                : 'bg-yellow-600 hover:bg-yellow-700'
                            } text-white`}
                            data-testid="debt-request-otp-btn"
                          >
                            {otpLoading ? (
                              <>
                                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                Envoi...
                              </>
                            ) : (
                              <>
                                <Send className="w-4 h-4 mr-2" />
                                Demander le code OTP
                              </>
                            )}
                          </Button>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <div>
                            <Label className={`text-xs ${paymentForm.paymentMethod === 'orange_money' ? 'text-orange-700' : 'text-yellow-700'}`}>
                              Code OTP reçu par SMS
                            </Label>
                            <div className="flex gap-2 mt-1">
                              <Input
                                type="text"
                                maxLength={6}
                                value={otpCode}
                                onChange={(e) => {
                                  setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6));
                                  setOtpError('');
                                }}
                                placeholder="Code à 6 chiffres"
                                className="flex-1 bg-white text-center text-sm tracking-widest font-mono h-9"
                                data-testid="debt-otp-input"
                              />
                              <Button
                                type="button"
                                size="sm"
                                onClick={handleVerifyOtp}
                                disabled={otpLoading || otpCode.length < 4}
                                className={`${
                                  paymentForm.paymentMethod === 'orange_money' 
                                    ? 'bg-orange-600 hover:bg-orange-700' 
                                    : 'bg-yellow-600 hover:bg-yellow-700'
                                } text-white h-9`}
                                data-testid="debt-verify-otp-btn"
                              >
                                {otpLoading ? (
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                  <CheckCircle className="w-4 h-4" />
                                )}
                              </Button>
                            </div>
                          </div>
                          
                          {otpError && (
                            <p className="text-xs text-red-600 flex items-center gap-1">
                              <X className="w-3 h-3" />
                              {otpError}
                            </p>
                          )}
                          
                          <div className="flex items-center justify-between text-xs">
                            <span className={paymentForm.paymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}>
                              Code non reçu?
                            </span>
                            {otpCountdown > 0 ? (
                              <span className="text-slate-500">
                                Renvoyer dans {otpCountdown}s
                              </span>
                            ) : (
                              <button
                                type="button"
                                onClick={handleRequestOtp}
                                disabled={otpLoading}
                                className={`flex items-center gap-1 font-medium ${
                                  paymentForm.paymentMethod === 'orange_money' 
                                    ? 'text-orange-700 hover:text-orange-800' 
                                    : 'text-yellow-700 hover:text-yellow-800'
                                }`}
                              >
                                <RefreshCw className="w-3 h-3" />
                                Renvoyer
                              </button>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
              
              {/* Notes */}
              <div>
                <Label htmlFor="notes">Notes (optionnel)</Label>
                <Input
                  id="notes"
                  value={paymentForm.notes}
                  onChange={(e) => setPaymentForm({ ...paymentForm, notes: e.target.value })}
                  placeholder="Ex: Paiement partiel..."
                  className="mt-1"
                />
              </div>
              
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setShowPaymentDialog(false)}>
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  className="bg-green-600 hover:bg-green-700"
                  disabled={createBulkPayment.isPending || (isMobileMoneyPayment && !otpVerified)}
                  data-testid="debt-submit-payment-btn"
                >
                  {createBulkPayment.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Encaisser
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Dialog Détail Client */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Détail des dettes - {selectedCustomer?.customer_name}
            </DialogTitle>
          </DialogHeader>
          
          {selectedCustomer && (
            <div className="space-y-4">
              {/* Résumé */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-red-50 rounded-lg text-center">
                  <p className="text-sm text-red-600">Dette Totale</p>
                  <p className="text-xl font-bold text-red-700">{formatAmount(selectedCustomer.total_debt)}</p>
                </div>
                <div className="p-4 bg-slate-50 rounded-lg text-center">
                  <p className="text-sm text-slate-600">Seuil Max</p>
                  <p className="text-xl font-bold text-slate-700">{formatAmount(selectedCustomer.max_debt_limit)}</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg text-center">
                  <p className="text-sm text-green-600">Crédit Dispo.</p>
                  <p className="text-xl font-bold text-green-700">{formatAmount(selectedCustomer.available_credit)}</p>
                </div>
              </div>
              
              {/* Liste des dettes */}
              <div>
                <h4 className="font-medium text-slate-900 mb-3">Historique des dettes</h4>
                {debtsLoading ? (
                  <SkeletonTable rows={3} columns={4} />
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50">
                        <tr>
                          <th className="px-4 py-2 text-left">Date</th>
                          <th className="px-4 py-2 text-left">Vente</th>
                          <th className="px-4 py-2 text-right">Montant</th>
                          <th className="px-4 py-2 text-right">Reste</th>
                          <th className="px-4 py-2 text-center">Statut</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {selectedCustomerDebts.map((debt) => (
                          <tr key={debt.id} className="hover:bg-slate-50">
                            <td className="px-4 py-2 text-slate-600">{formatDate(debt.created_at)}</td>
                            <td className="px-4 py-2 font-mono text-xs">{debt.sale_number}</td>
                            <td className="px-4 py-2 text-right">{formatAmount(debt.original_amount)}</td>
                            <td className="px-4 py-2 text-right font-medium text-red-600">
                              {formatAmount(debt.remaining_amount)}
                            </td>
                            <td className="px-4 py-2 text-center">
                              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                                debt.status === 'paid' 
                                  ? 'bg-green-100 text-green-700'
                                  : debt.status === 'partial'
                                  ? 'bg-yellow-100 text-yellow-700'
                                  : 'bg-red-100 text-red-700'
                              }`}>
                                {debt.status === 'paid' ? 'Payé' : debt.status === 'partial' ? 'Partiel' : 'En cours'}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {selectedCustomerDebts.length === 0 && (
                      <div className="text-center py-8">
                        <p className="text-slate-500">Aucune dette</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      
      {/* Dialog Abandon de Dette */}
      <Dialog open={showWriteOffDialog} onOpenChange={setShowWriteOffDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600" style={{ fontFamily: 'Manrope, sans-serif' }}>
              <XCircle className="w-5 h-5" />
              Abandonner la dette
            </DialogTitle>
          </DialogHeader>
          
          {selectedDebtForWriteOff && (
            <form onSubmit={handleSubmitWriteOff} className="space-y-4">
              {/* Avertissement */}
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-red-800">Action irréversible</p>
                    <p className="text-xs text-red-600 mt-1">
                      Cette action va passer en perte toutes les dettes de ce client. 
                      L&apos;opération sera tracée dans l&apos;historique pour la comptabilité.
                    </p>
                    <p className="text-xs text-red-600 mt-1 font-medium">
                      ⚠️ Le seuil de crédit du client sera automatiquement mis à zéro.
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Récapitulatif */}
              <div className="p-4 bg-slate-50 rounded-lg space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm text-slate-600">Client:</span>
                  <span className="text-sm font-medium text-slate-900">{selectedDebtForWriteOff.customer_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-600">Montant à abandonner:</span>
                  <span className="text-sm font-bold text-red-600">{formatAmount(selectedDebtForWriteOff.total_debt)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm text-slate-600">Nombre de dettes:</span>
                  <span className="text-sm font-medium text-slate-900">{selectedDebtForWriteOff.debts_count}</span>
                </div>
                <div className="flex justify-between border-t border-slate-200 pt-2 mt-2">
                  <span className="text-sm text-slate-600">Nouveau seuil crédit:</span>
                  <span className="text-sm font-bold text-red-600">0 GNF</span>
                </div>
              </div>
              
              {/* Raison obligatoire */}
              <div>
                <Label htmlFor="writeOffReason" className="text-red-700">
                  Raison de l&apos;abandon <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="writeOffReason"
                  value={writeOffReason}
                  onChange={(e) => setWriteOffReason(e.target.value)}
                  placeholder="Ex: Client décédé, insolvabilité, accord commercial..."
                  className="mt-1"
                  required
                  data-testid="write-off-reason-input"
                />
                <p className="text-xs text-slate-500 mt-1">
                  Cette raison sera enregistrée pour la traçabilité comptable
                </p>
              </div>
              
              <DialogFooter>
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setShowWriteOffDialog(false)}
                >
                  Annuler
                </Button>
                <Button 
                  type="submit" 
                  className="bg-green-600 hover:bg-green-700 text-white"
                  disabled={writeOffDebt.isPending || !writeOffReason.trim()}
                  data-testid="write-off-confirm-btn"
                >
                  {writeOffDebt.isPending && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  <Trash2 className="w-4 h-4 mr-2" />
                  Confirmer l&apos;abandon
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Debts;
