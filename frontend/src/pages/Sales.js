import React, { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Search, ShoppingCart, X, Eye, CreditCard, Banknote, FileCheck, FileText, RotateCcw, History, Filter, Calendar, ScanLine, WifiOff, CloudOff, Loader2, Smartphone, Percent, DollarSign, CircleDollarSign, Wallet, Send, CheckCircle, RefreshCw, Shield, Clock, LogOut, Pause, Play, Trash2, AlertCircle, CalendarX, Timer, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Tag, Zap, Gift } from 'lucide-react';
import { addItem, getAllItems, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import api from '../services/api';
import { toast } from 'sonner';
import BarcodeScanner from '../components/BarcodeScanner';
import { createOfflineSale, isOffline as checkOffline } from '../services/offlineService';
import { useQueryClient } from '@tanstack/react-query';
import { useSales, useSalesInfinite, useCreateSale } from '../hooks/useSales';
import { useProducts } from '../hooks/useProducts';
import { useCustomers } from '../hooks/useCustomers';
import { useSettingsQuery } from '../hooks/useSettings';
import { useCreateReturn } from '../hooks/useReturns';
import { useOperationsHistoryInfinite } from '../hooks/useInfiniteScroll';
import { usePaymentMethods } from '../hooks/usePaymentMethods';
import { useCustomerAvailableCredit } from '../hooks/useDebts';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';
import { usePendingSales, usePendingSalesCount, useCreatePendingSale, useCancelPendingSale } from '../hooks/usePendingSales';
import { SkeletonSalesPage } from '../components/ui/skeleton-shimmer';
import { useAuth } from '../contexts/AuthContext';

// Composant pour le formulaire de rabais par produit
const ProductDiscountForm = ({ item, onApply, onCancel }) => {
  const [type, setType] = useState('percent');
  const [value, setValue] = useState(item.discount_value?.toString() || '');
  const [reason, setReason] = useState(item.discount_reason || '');

  const subtotal = item.price * item.quantity;
  const previewAmount = type === 'percent' 
    ? Math.round(subtotal * (parseFloat(value) || 0) / 100)
    : Math.min(parseFloat(value) || 0, subtotal);

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <div className="flex gap-1 bg-green-100 rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setType('percent')}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              type === 'percent' ? 'bg-white text-green-800 shadow-sm' : 'text-green-600'
            }`}
          >
            %
          </button>
          <button
            type="button"
            onClick={() => setType('amount')}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              type === 'amount' ? 'bg-white text-green-800 shadow-sm' : 'text-green-600'
            }`}
          >
            GNF
          </button>
        </div>
        <Input
          type="number"
          min="0"
          max={type === 'percent' ? 100 : subtotal}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Valeur"
          className="w-24 bg-white"
        />
        <Input
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Motif (optionnel)"
          className="flex-1 bg-white text-sm"
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-sm text-green-600">
          Aperçu: -{type === 'percent' ? `${value || 0}%` : `${value || 0} GNF`} = -{previewAmount.toLocaleString()} GNF
        </span>
        <div className="flex gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
            Annuler
          </Button>
          <Button 
            type="button" 
            size="sm" 
            onClick={() => onApply(type, value, reason)}
            disabled={!value || parseFloat(value) <= 0}
            className="bg-green-600 hover:bg-green-700"
          >
            Appliquer
          </Button>
        </div>
      </div>
    </div>
  );
};

const Sales = () => {
  const { isOnline } = useOffline();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  // État des filtres
  const [searchQuery, setSearchQuery] = useState('');
  const [searchDate, setSearchDate] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [salesViewFilter, setSalesViewFilter] = useState('completed'); // 'completed', 'credit', 'partial', 'all'
  
  // Ref pour l'intersection observer (infinite scroll)
  const loadMoreRef = useRef(null);
  
  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // React Query hooks avec infinite scroll
  const { 
    data: salesData,
    isLoading: salesLoading, 
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch: refetchSales 
  } = useSalesInfinite({
    limit: 20,
    search: debouncedSearch,
    dateFrom: searchDate,
    dateTo: searchDate,
    status: salesViewFilter === 'all' ? '' : salesViewFilter
  });
  
  // Aplatir les pages en une seule liste
  const sales = salesData?.pages?.flatMap(page => page.items) || [];
  const totalSales = salesData?.pages?.[0]?.total || 0;
  
  // Intersection Observer pour charger plus de données au scroll
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { threshold: 0.1 }
    );
    
    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }
    
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  
  const { data: products = [], isLoading: productsLoading } = useProducts();
  const { data: customers = [], isLoading: customersLoading } = useCustomers();
  const { data: appSettings = { currency: 'GNF' } } = useSettingsQuery();
  
  // Historique des opérations avec infinite scroll
  const historyScrollRef = useRef(null);
  const { 
    data: operationsHistoryData,
    isLoading: historyLoading,
    isFetchingNextPage: historyFetchingNext,
    hasNextPage: historyHasNext,
    fetchNextPage: fetchNextHistoryPage,
    refetch: refetchHistory 
  } = useOperationsHistoryInfinite({
    limit: 20,
    type_filter: 'all'
  });
  
  const operationsHistory = operationsHistoryData?.pages?.flatMap(page => page.items) || [];
  const totalOperations = operationsHistoryData?.pages?.[0]?.total || 0;
  
  const { data: paymentMethods = [], isLoading: paymentMethodsLoading } = usePaymentMethods(true); // activeOnly=true
  
  // Ventes en attente
  const { data: pendingSales = [], isLoading: pendingSalesLoading, refetch: refetchPendingSales } = usePendingSales('pending');
  const { data: pendingSalesCount } = usePendingSalesCount();
  const createPendingSale = useCreatePendingSale();
  const cancelPendingSale = useCancelPendingSale();
  
  // Shift management - Les modales sont gérées globalement dans Layout.js
  const { data: currentShift } = useCurrentShift();
  // Vérifier si l'utilisateur peut effectuer des opérations (admin exempté)
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // Vérifier l'éligibilité de planification (pour restreindre l'accès hors horaires)
  const { data: shiftEligibility } = useShiftEligibility();
  const isAdmin = user?.role === 'admin';
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  // Mutations
  const createSale = useCreateSale();
  const createReturn = useCreateReturn();

  // Local state
  const [showDialog, setShowDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showReturnDialog, setShowReturnDialog] = useState(false);
  const [showHistoryDialog, setShowHistoryDialog] = useState(false);
  const [showReturnDetailDialog, setShowReturnDetailDialog] = useState(false);
  const [showPendingSalesDialog, setShowPendingSalesDialog] = useState(false);
  const [selectedSale, setSelectedSale] = useState(null);
  const [selectedReturnDetail, setSelectedReturnDetail] = useState(null);
  const [returnItems, setReturnItems] = useState([]);
  const [returnReason, setReturnReason] = useState('');
  const [historyFilter, setHistoryFilter] = useState('all'); // all, sales, returns
  const [saleReturns, setSaleReturns] = useState({});
  const [returnEligibility, setReturnEligibility] = useState(null);
  const [cart, setCart] = useState([]);
  const [selectedCustomer, setSelectedCustomer] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [discountType, setDiscountType] = useState('percent'); // 'percent' ou 'amount'
  const [discountValue, setDiscountValue] = useState('');
  // Détails de paiement selon le mode
  const [paymentDetails, setPaymentDetails] = useState({
    // Orange Money
    orange_sender_number: '',
    orange_ticket_ref: '',
    // MTN Money
    mtn_sender_number: '',
    mtn_ticket_ref: '',
    // Chèque
    check_holder_name: '',
    check_number: '',
    check_bank: '',
    // Carte bancaire
    card_holder_name: '',
    card_last_digits: '',
    card_bank: '',
  });
  const [productSearch, setProductSearch] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');
  const [showCustomerDropdown, setShowCustomerDropdown] = useState(false);
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);
  
  // États pour le paiement mixte (2 modes de paiement)
  const [useMixedPayment, setUseMixedPayment] = useState(false);
  const [secondPaymentMethod, setSecondPaymentMethod] = useState('');
  const [firstPaymentAmount, setFirstPaymentAmount] = useState('');
  const [secondPaymentAmount, setSecondPaymentAmount] = useState('');
  const [secondPaymentDetails, setSecondPaymentDetails] = useState({
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
  
  // États pour la dette (en plus du paiement mixte)
  const [useDebtPayment, setUseDebtPayment] = useState(false);
  const [debtAmount, setDebtAmount] = useState('');
  
  // États pour OTP (Mobile Money) - Premier mode
  const [otpCode, setOtpCode] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [otpVerified, setOtpVerified] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpError, setOtpError] = useState('');
  const [otpCountdown, setOtpCountdown] = useState(0);
  
  // États pour le code promo
  const [promoCode, setPromoCode] = useState('');
  const [promoCodeValidation, setPromoCodeValidation] = useState(null); // {valid, discount_amount, ...}
  const [promoCodeLoading, setPromoCodeLoading] = useState(false);
  const [promoCodeError, setPromoCodeError] = useState('');
  
  // États pour les rabais automatiques
  const [automaticDiscounts, setAutomaticDiscounts] = useState([]);
  const [automaticDiscountsLoading, setAutomaticDiscountsLoading] = useState(false);
  const [showProductDiscount, setShowProductDiscount] = useState(null); // index du produit à modifier
  
  // États pour OTP (Mobile Money) - Second mode (paiement mixte)
  const [secondOtpCode, setSecondOtpCode] = useState('');
  const [secondOtpSent, setSecondOtpSent] = useState(false);
  const [secondOtpVerified, setSecondOtpVerified] = useState(false);
  const [secondOtpLoading, setSecondOtpLoading] = useState(false);
  const [secondOtpError, setSecondOtpError] = useState('');
  const [secondOtpCountdown, setSecondOtpCountdown] = useState(0);
  
  // Vérifie si le mode de paiement actuel est Mobile Money
  const isMobileMoneyPayment = paymentMethod === 'orange_money' || paymentMethod === 'mtn_money';
  const isSecondMobileMoneyPayment = secondPaymentMethod === 'orange_money' || secondPaymentMethod === 'mtn_money';
  
  // Obtenir le téléphone du client sélectionné (pour le champ N° Expéditeur)
  const getSelectedCustomerPhone = () => {
    if (selectedCustomer && selectedCustomer !== 'none') {
      const customer = customers.find(c => c.id === selectedCustomer);
      if (customer?.phone) {
        return customer.phone;
      }
    }
    return '';
  };
  
  // Obtenir le numéro OTP par défaut des paramètres (pour l'envoi du code OTP)
  const getDefaultOtpPhone = (method = paymentMethod) => {
    if (method === 'orange_money' && appSettings?.orange_money_default_phone) {
      return appSettings.orange_money_default_phone;
    }
    if (method === 'mtn_money' && appSettings?.mtn_money_default_phone) {
      return appSettings.mtn_money_default_phone;
    }
    return '';
  };
  
  // Hook pour vérifier le crédit disponible du client sélectionné
  const { data: customerCredit, isLoading: creditLoading } = useCustomerAvailableCredit(selectedCustomer);

  // Fonction pour formater avec la devise chargée
  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  const refreshData = async () => {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      }
      
      try {
        const db = await getDB();
        await db.clear('sales');
      } catch (error) {
        console.warn('Could not clear IndexedDB:', error);
      }
      
      await Promise.all([
        refetchSales(),
        refetchHistory(),
        queryClient.invalidateQueries({ queryKey: ['products'] }),
      ]);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  const addToCart = (product) => {
    if (product.stock <= 0) {
      toast.error('Produit en rupture de stock');
      return;
    }
    
    const existing = cart.find((item) => item.product_id === product.id);
    if (existing) {
      if (existing.quantity >= product.stock) {
        toast.error('Stock insuffisant');
        return;
      }
      setCart(
        cart.map((item) =>
          item.product_id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      );
    } else {
      setCart([...cart, { product_id: product.id, name: product.name, price: product.price, quantity: 1, max_stock: product.stock }]);
    }
    toast.success(`${product.name} ajouté au panier`);
    setProductSearch(''); // Vider le champ de recherche après ajout
  };

  const removeFromCart = (productId) => {
    setCart(cart.filter((item) => item.product_id !== productId));
  };

  const updateQuantity = (productId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(productId);
      return;
    }
    const item = cart.find(i => i.product_id === productId);
    if (item && quantity > item.max_stock) {
      toast.error('Stock insuffisant');
      return;
    }
    setCart(
      cart.map((item) =>
        item.product_id === productId ? { ...item, quantity: parseInt(quantity) } : item
      )
    );
  };

  // Appliquer un rabais sur un produit individuel
  const applyProductDiscount = (productId, type, value, reason = '') => {
    setCart(
      cart.map((item) => {
        if (item.product_id === productId) {
          const subtotal = item.price * item.quantity;
          let discountAmount = 0;
          if (type === 'percent') {
            // Calcul précis du pourcentage avec arrondi correct
            discountAmount = Math.round((subtotal * (parseFloat(value) || 0)) / 100 * 100) / 100;
          } else {
            discountAmount = Math.min(parseFloat(value) || 0, subtotal);
          }
          // Arrondir au GNF entier pour éviter les décimales
          discountAmount = Math.round(discountAmount);
          return {
            ...item,
            discount_type: type,
            discount_value: parseFloat(value) || 0,
            discount_amount: discountAmount,
            discount_reason: reason,
            final_subtotal: subtotal - discountAmount
          };
        }
        return item;
      })
    );
    setShowProductDiscount(null);
    toast.success('Rabais appliqué');
  };

  // Supprimer le rabais d'un produit
  const removeProductDiscount = (productId) => {
    setCart(
      cart.map((item) => {
        if (item.product_id === productId) {
          const { discount_type, discount_value, discount_amount, discount_reason, final_subtotal, ...rest } = item;
          return rest;
        }
        return item;
      })
    );
  };

  // Valider un code promo
  const validatePromoCode = async () => {
    if (!promoCode.trim()) {
      toast.error('Veuillez saisir un code promo');
      return;
    }

    setPromoCodeLoading(true);
    setPromoCodeError('');
    
    try {
      const response = await api.post('/discounts/promo-codes/validate', {
        code: promoCode.trim(),
        cart_subtotal: calculateSubtotal(),
        customer_id: selectedCustomer && selectedCustomer !== 'none' ? selectedCustomer : null,
        cart_items: cart.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          subtotal: item.price * item.quantity
        }))
      });
      
      setPromoCodeValidation(response.data);
      toast.success(`Code promo valide ! Réduction: ${formatAmount(response.data.discount_amount)}`);
    } catch (error) {
      const message = error.response?.data?.detail || 'Code promo invalide';
      setPromoCodeError(message);
      setPromoCodeValidation(null);
      toast.error(message);
    } finally {
      setPromoCodeLoading(false);
    }
  };

  // Supprimer le code promo
  const removePromoCode = () => {
    setPromoCode('');
    setPromoCodeValidation(null);
    setPromoCodeError('');
  };

  // Calculer le sous-total avant rabais (inclut les rabais produit)
  const calculateSubtotal = () => {
    return cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  };

  // Calculer les rabais automatiques
  const calculateAutomaticDiscounts = async () => {
    if (cart.length === 0) {
      setAutomaticDiscounts([]);
      return;
    }

    setAutomaticDiscountsLoading(true);
    try {
      const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
      const response = await api.post('/discounts/calculate', {
        cart_subtotal: subtotal,
        customer_id: selectedCustomer && selectedCustomer !== 'none' ? selectedCustomer : null,
        cart_items: cart.map(item => ({
          product_id: item.product_id,
          quantity: item.quantity,
          subtotal: item.price * item.quantity,
          category_id: item.category_id || null,
          expiry_date: item.expiry_date || null
        })),
        promo_code: null // On ne passe pas le code ici, il est géré séparément
      });
      
      const discounts = response.data.automatic_discounts || [];
      setAutomaticDiscounts(discounts);
      
      // Notifier si de nouveaux rabais ont été appliqués
      if (discounts.length > 0 && automaticDiscounts.length === 0) {
        toast.info(`${discounts.length} rabais automatique(s) appliqué(s)!`, { duration: 3000 });
      }
    } catch (error) {
      console.error('Error calculating automatic discounts:', error);
      // Ne pas effacer les rabais existants en cas d'erreur réseau
    } finally {
      setAutomaticDiscountsLoading(false);
    }
  };

  // Recalculer les rabais automatiques quand le panier ou le client change
  useEffect(() => {
    const timer = setTimeout(() => {
      calculateAutomaticDiscounts();
    }, 500); // Debounce de 500ms pour éviter trop d'appels
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cart.length, selectedCustomer, JSON.stringify(cart.map(i => ({ id: i.product_id, qty: i.quantity })))]);

  // Calculer le sous-total avant rabais (déjà défini ci-dessus, supprimé le doublon)

  // Calculer le total des rabais produit
  const calculateProductDiscounts = () => {
    return cart.reduce((sum, item) => sum + (item.discount_amount || 0), 0);
  };

  // Calculer le total des rabais automatiques
  const calculateAutomaticDiscountAmount = () => {
    return automaticDiscounts.reduce((sum, d) => sum + (d.discount_amount || 0), 0);
  };

  // Calculer le montant du rabais manuel (existant)
  const calculateManualDiscountAmount = () => {
    const subtotal = calculateSubtotal() - calculateProductDiscounts() - calculateAutomaticDiscountAmount();
    const value = parseFloat(discountValue) || 0;
    if (discountType === 'percent') {
      // Calcul précis du pourcentage avec arrondi correct
      const discountAmount = (subtotal * value) / 100;
      return Math.round(discountAmount * 100) / 100; // Arrondir à 2 décimales puis au GNF entier
    }
    return Math.min(value, subtotal);
  };

  // Calculer le montant total des rabais (tous types confondus)
  const calculateDiscountAmount = () => {
    const productDiscounts = calculateProductDiscounts();
    const autoDiscounts = calculateAutomaticDiscountAmount();
    const promoDiscount = promoCodeValidation?.discount_amount || 0;
    const manualDiscount = calculateManualDiscountAmount();
    
    return productDiscounts + autoDiscounts + promoDiscount + manualDiscount;
  };

  // Calculer le total après rabais
  const calculateTotal = () => {
    return Math.max(0, calculateSubtotal() - calculateDiscountAmount());
  };

  // Valider les détails de paiement - DYNAMIQUE avec validations avancées
  const validatePaymentDetails = () => {
    const selectedMethod = paymentMethods.find(m => m.code === paymentMethod);
    
    // Si pas de méthode sélectionnée ou pas de champs requis, valide
    if (!selectedMethod || !selectedMethod.required_fields || selectedMethod.required_fields.length === 0) {
      return true;
    }
    
    // Vérifier chaque champ requis
    for (const field of selectedMethod.required_fields) {
      if (field.required) {
        const fieldKey = `${paymentMethod}_${field.name}`;
        const value = paymentDetails[fieldKey] || '';
        const trimmedValue = typeof value === 'string' ? value.trim() : value;
        
        // Vérification champ vide
        if (!trimmedValue) {
          toast.error(`Veuillez saisir: ${field.label}`);
          return false;
        }
        
        // Validation longueur minimale
        if (field.minLength && trimmedValue.length < field.minLength) {
          toast.error(`${field.label} doit contenir au moins ${field.minLength} caractères`);
          return false;
        }
        
        // Validation longueur exacte (ex: 4 derniers chiffres carte)
        if (field.maxLength && field.name === 'last_digits' && trimmedValue.length !== field.maxLength) {
          toast.error(`${field.label} doit contenir exactement ${field.maxLength} chiffres`);
          return false;
        }
        
        // Validation numéro de téléphone (type tel)
        if (field.type === 'tel') {
          const phoneRegex = /^[0-9\s\-+()]+$/;
          if (!phoneRegex.test(trimmedValue)) {
            toast.error(`${field.label}: format de numéro invalide`);
            return false;
          }
          // Vérifier longueur min pour téléphone
          const digitsOnly = trimmedValue.replace(/\D/g, '');
          if (digitsOnly.length < 8) {
            toast.error(`${field.label}: numéro trop court (minimum 8 chiffres)`);
            return false;
          }
        }
        
        // Validation référence marchand (format alphanumérique avec points)
        if (field.name === 'ticket_ref') {
          const refRegex = /^[A-Za-z0-9.\-_]+$/;
          if (!refRegex.test(trimmedValue)) {
            toast.error(`${field.label}: format invalide (lettres, chiffres et points uniquement)`);
            return false;
          }
        }
        
        // Validation numéro de chèque (chiffres uniquement)
        if (field.name === 'check_number') {
          const checkRegex = /^[0-9]+$/;
          if (!checkRegex.test(trimmedValue)) {
            toast.error(`${field.label}: doit contenir uniquement des chiffres`);
            return false;
          }
        }
        
        // Validation 4 derniers chiffres carte (chiffres uniquement)
        if (field.name === 'last_digits') {
          const digitsRegex = /^[0-9]+$/;
          if (!digitsRegex.test(trimmedValue)) {
            toast.error(`${field.label}: doit contenir uniquement des chiffres`);
            return false;
          }
        }
      }
    }
    
    return true;
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
    setSecondPaymentDetails({
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

  // Réinitialiser le paiement mixte
  const resetMixedPayment = () => {
    setUseMixedPayment(false);
    setSecondPaymentMethod('');
    setFirstPaymentAmount('');
    setSecondPaymentAmount('');
    resetPaymentDetails();
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

  // Effet pour pré-remplir le numéro de téléphone du client pour Mobile Money
  React.useEffect(() => {
    if (isMobileMoneyPayment) {
      // Pré-remplir uniquement avec le numéro du client sélectionné
      const customerPhone = getSelectedCustomerPhone();
      const fieldKey = `${paymentMethod}_sender_number`;
      setPaymentDetails(prev => ({
        ...prev,
        [fieldKey]: customerPhone // Vide si pas de client ou client sans téléphone
      }));
    }
    // Reset OTP state when payment method changes
    resetOtpState();
  }, [paymentMethod, selectedCustomer]);

  // Effet pour pré-remplir le numéro de téléphone pour le second mode de paiement (Mobile Money)
  React.useEffect(() => {
    if (isSecondMobileMoneyPayment && useMixedPayment) {
      // Pré-remplir avec le numéro du client sélectionné
      const customerPhone = getSelectedCustomerPhone();
      const fieldKey = `${secondPaymentMethod}_sender_number`;
      setSecondPaymentDetails(prev => ({
        ...prev,
        [fieldKey]: customerPhone
      }));
      // Reset second OTP state when second payment method changes
      resetSecondOtpState();
    }
  }, [secondPaymentMethod, selectedCustomer, useMixedPayment]);

  // Effet pour calculer automatiquement le second montant en paiement mixte
  React.useEffect(() => {
    if (useMixedPayment && firstPaymentAmount) {
      const total = calculateTotal();
      const first = parseFloat(firstPaymentAmount) || 0;
      const remaining = Math.max(0, total - first);
      setSecondPaymentAmount(remaining.toString());
    }
  }, [firstPaymentAmount, useMixedPayment, cart, discountValue, discountType]);

  // Effet pour le compte à rebours OTP (premier mode)
  React.useEffect(() => {
    if (otpCountdown > 0) {
      const timer = setTimeout(() => setOtpCountdown(otpCountdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [otpCountdown]);

  // Effet pour le compte à rebours OTP (second mode)
  React.useEffect(() => {
    if (secondOtpCountdown > 0) {
      const timer = setTimeout(() => setSecondOtpCountdown(secondOtpCountdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [secondOtpCountdown]);

  // Réinitialiser l'état OTP du second mode
  const resetSecondOtpState = () => {
    setSecondOtpCode('');
    setSecondOtpSent(false);
    setSecondOtpVerified(false);
    setSecondOtpLoading(false);
    setSecondOtpError('');
    setSecondOtpCountdown(0);
  };

  // Demander un code OTP pour le second mode (simulation)
  const handleRequestSecondOtp = async () => {
    const otpTargetNumber = getDefaultOtpPhone(secondPaymentMethod);
    
    if (!otpTargetNumber) {
      setSecondOtpError('Aucun numéro OTP configuré dans les paramètres');
      return;
    }
    
    setSecondOtpLoading(true);
    setSecondOtpError('');
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      setSecondOtpSent(true);
      setSecondOtpCountdown(60);
      toast.success(`Code OTP envoyé au ${otpTargetNumber}`, {
        description: 'Pour la démo, utilisez le code: 123456'
      });
    } catch (error) {
      setSecondOtpError('Erreur lors de l\'envoi du code OTP');
      toast.error('Échec de l\'envoi du code OTP');
    } finally {
      setSecondOtpLoading(false);
    }
  };

  // Vérifier le code OTP du second mode (simulation)
  const handleVerifySecondOtp = async () => {
    if (!secondOtpCode || secondOtpCode.length < 4) {
      setSecondOtpError('Veuillez saisir le code OTP complet');
      return;
    }
    
    setSecondOtpLoading(true);
    setSecondOtpError('');
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      if (secondOtpCode === '123456') {
        setSecondOtpVerified(true);
        setSecondOtpError('');
        toast.success('Code OTP validé avec succès!');
      } else {
        setSecondOtpError('Code OTP incorrect. Pour la démo, utilisez: 123456');
        toast.error('Code OTP incorrect');
      }
    } catch (error) {
      setSecondOtpError('Erreur lors de la vérification du code');
    } finally {
      setSecondOtpLoading(false);
    }
  };

  // Demander un code OTP (simulation)
  const handleRequestOtp = async () => {
    // Le code OTP est envoyé au numéro configuré dans les Paramètres
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
      
      // En production, ceci appellerait l'API Mobile Money 
      //   phone: otpTargetNumber, 
      //   provider: paymentMethod,
      //   amount: calculateTotal()
      // });
      
      setOtpSent(true);
      setOtpCountdown(60); // 60 secondes avant de pouvoir renvoyer
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
      
      // En production: appel API pour vérifier le code
      // const response = await api.post('/payments/verify-otp', { 
      //   phone: paymentDetails[`${paymentMethod}_sender_number`],
      //   code: otpCode,
      //   provider: paymentMethod
      // });
      
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

  // ============================================
  // GESTION DES VENTES EN ATTENTE
  // ============================================
  
  // Mettre une vente en attente
  const handlePutOnHold = async () => {
    if (cart.length === 0) {
      toast.error('Le panier est vide');
      return;
    }
    
    const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    const discountAmount = calculateDiscountAmount();
    const total = subtotal - discountAmount;
    
    const pendingSaleData = {
      customer_id: selectedCustomer && selectedCustomer !== 'none' ? selectedCustomer : null,
      items: cart.map(item => ({
        product_id: item.product_id,
        product_name: item.name,
        quantity: Number(item.quantity) || 1,
        unit_price: Number(item.price) || 0,
      })),
      subtotal: Number(subtotal) || 0,
      discount_type: discountValue && !isNaN(parseFloat(discountValue)) && parseFloat(discountValue) > 0 ? discountType : null,
      discount_value: discountValue && !isNaN(parseFloat(discountValue)) ? Number(parseFloat(discountValue)) : 0,
      discount_amount: Number(discountAmount) || 0,
      total: Number(total) || 0,
      notes: null,
    };
    
    console.log('Pending sale data:', JSON.stringify(pendingSaleData));
    
    createPendingSale.mutate(pendingSaleData, {
      onSuccess: (data) => {
        toast.success(`Vente mise en attente (${data.reference}) - Expire dans ${data.expires_in_hours}h`);
        // Vider le panier
        setCart([]);
        setSelectedCustomer('');
        setCustomerSearch('');
        setDiscountType('percent');
        setDiscountValue('');
        setShowDialog(false);
      },
      onError: (error) => {
        const detail = error.response?.data?.detail;
        let errorMessage = 'Erreur lors de la mise en attente';
        if (typeof detail === 'string') {
          errorMessage = detail;
        } else if (Array.isArray(detail) && detail.length > 0) {
          errorMessage = detail[0]?.msg || errorMessage;
        }
        toast.error(errorMessage);
      }
    });
  };
  
  // Reprendre une vente en attente
  const handleResumePendingSale = (pendingSale) => {
    // Charger les items dans le panier (le cart utilise 'price', pas 'unit_price')
    const cartItems = pendingSale.items.map(item => ({
      product_id: item.product_id,
      name: item.product_name,
      price: item.unit_price,
      quantity: item.quantity,
    }));
    
    setCart(cartItems);
    setSelectedCustomer(pendingSale.customer_id || '');
    setCustomerSearch(pendingSale.customer_name || '');
    
    // Charger les remises
    if (pendingSale.discount_type) {
      setDiscountType(pendingSale.discount_type);
      setDiscountValue(pendingSale.discount_value?.toString() || '');
    } else {
      setDiscountType('percent');
      setDiscountValue('');
    }
    
    // Annuler la vente en attente (elle sera recréée ou finalisée)
    cancelPendingSale.mutate(pendingSale.id, {
      onSuccess: () => {
        toast.info(`Vente ${pendingSale.reference} chargée dans le panier`);
        setShowPendingSalesDialog(false);
        setShowDialog(true);
      },
      onError: () => {
        // Même si l'annulation échoue, on continue
        toast.info(`Vente ${pendingSale.reference} chargée dans le panier`);
        setShowPendingSalesDialog(false);
        setShowDialog(true);
      }
    });
  };
  
  // Annuler une vente en attente
  const handleCancelPendingSale = (pendingSale) => {
    if (window.confirm(`Annuler la vente en attente ${pendingSale.reference} ?`)) {
      cancelPendingSale.mutate(pendingSale.id, {
        onSuccess: () => {
          toast.success(`Vente ${pendingSale.reference} annulée`);
        },
        onError: (error) => {
          toast.error(error.response?.data?.detail || 'Erreur lors de l\'annulation');
        }
      });
    }
  };
  
  // Formater le temps restant
  const formatTimeRemaining = (minutes) => {
    if (minutes <= 0) return 'Expirée';
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}min`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (cart.length === 0) {
      toast.error('Le panier est vide');
      return;
    }

    // Valider les détails de paiement
    if (!validatePaymentDetails()) {
      return;
    }
    
    // Validation OTP - DÉSACTIVÉE (En cours de développement)
    // if (isMobileMoneyPayment && !otpVerified) {
    //   toast.error('Veuillez valider le code OTP pour finaliser le paiement Mobile Money');
    //   return;
    // }
    
    // Validation des champs obligatoires Mobile Money (OTP désactivé)
    if (isMobileMoneyPayment) {
      const recipientNumber = paymentMethod === 'orange_money' ? paymentDetails.orange_money_sender_number : paymentDetails.mtn_money_sender_number;
      const ticketRef = paymentMethod === 'orange_money' ? paymentDetails.orange_money_ticket_ref : paymentDetails.mtn_money_ticket_ref;
      
      if (!recipientNumber || recipientNumber.trim() === '') {
        toast.error('Veuillez saisir le numéro destinataire');
        return;
      }
      if (!ticketRef || ticketRef.trim() === '') {
        toast.error('Veuillez saisir la référence du paiement marchand');
        return;
      }
    }
    
    const total = calculateTotal();

    // Validation pour le paiement mixte (2 modes)
    if (useMixedPayment) {
      if (!secondPaymentMethod) {
        toast.error('Veuillez sélectionner le second mode de paiement');
        return;
      }
      
      const totalPayments = (parseFloat(firstPaymentAmount) || 0) + (parseFloat(secondPaymentAmount) || 0);
      if (Math.abs(totalPayments - total) > 0.01) {
        toast.error(`Le total des paiements (${formatAmount(totalPayments)}) ne correspond pas au montant de la vente (${formatAmount(total)})`);
        return;
      }
      
      // Validation OTP pour le second mode - DÉSACTIVÉE (En cours de développement)
      // if (isSecondMobileMoneyPayment && !secondOtpVerified) {
      //   toast.error('Veuillez valider le code OTP pour le second mode de paiement Mobile Money');
      //   return;
      // }
    }
    
    // Validation spéciale pour le paiement par dette
    if (paymentMethod === 'debt' || useDebtPayment) {
      // Un client doit être sélectionné
      if (!selectedCustomer || selectedCustomer === 'none') {
        toast.error('Veuillez sélectionner un client pour une vente à crédit');
        return;
      }
      
      // Vérifier le crédit disponible
      if (!customerCredit) {
        toast.error('Impossible de vérifier le crédit du client');
        return;
      }
      
      if (!customerCredit.can_use_credit) {
        toast.error(`${customerCredit.customer_name} n'est pas autorisé à acheter à crédit`);
        return;
      }
      
      const requestedDebt = paymentMethod === 'debt' ? total : parseFloat(debtAmount) || 0;
      
      if (requestedDebt > customerCredit.available_credit) {
        toast.error(`Crédit insuffisant. Disponible: ${formatAmount(customerCredit.available_credit)}`);
        return;
      }
    }

    const subtotal = calculateSubtotal();
    const discountAmount = calculateDiscountAmount();

    // Préparer les détails de paiement selon le mode - DYNAMIQUE
    let paymentDetailsData = null;
    const selectedMethod = paymentMethods.find(m => m.code === paymentMethod);
    
    if (selectedMethod && selectedMethod.required_fields && selectedMethod.required_fields.length > 0) {
      paymentDetailsData = {};
      for (const field of selectedMethod.required_fields) {
        const fieldKey = `${paymentMethod}_${field.name}`;
        paymentDetailsData[field.name] = paymentDetails[fieldKey] || '';
      }
    }

    // Préparer les détails du second paiement si paiement mixte (2 modes)
    let secondPaymentDetailsData = null;
    if (useMixedPayment && secondPaymentMethod) {
      const secondMethod = paymentMethods.find(m => m.code === secondPaymentMethod);
      if (secondMethod && secondMethod.required_fields && secondMethod.required_fields.length > 0) {
        secondPaymentDetailsData = {};
        for (const field of secondMethod.required_fields) {
          const fieldKey = `${secondPaymentMethod}_${field.name}`;
          secondPaymentDetailsData[field.name] = secondPaymentDetails[fieldKey] || '';
        }
      }
      
      // Validation: vérifier que les montants des paiements mixtes égalent le total
      const firstAmount = parseFloat(firstPaymentAmount) || 0;
      const secondAmount = parseFloat(secondPaymentAmount) || 0;
      const totalPayments = firstAmount + secondAmount;
      
      if (Math.abs(totalPayments - total) > 0.01) {
        toast.error(`Les montants des paiements (${formatAmount(totalPayments)}) ne correspondent pas au total (${formatAmount(total)})`);
        return;
      }
    }
    
    // Calculer les montants pour le paiement
    let amountPaid = total;
    let debtAmountValue = 0;
    
    if (paymentMethod === 'debt') {
      // Tout en dette
      amountPaid = 0;
      debtAmountValue = total;
    } else if (useDebtPayment && debtAmount) {
      // Paiement avec dette partielle
      debtAmountValue = parseFloat(debtAmount) || 0;
      amountPaid = total - debtAmountValue;
    }

    // Construire les données de vente
    const saleData = {
      customer_id: selectedCustomer && selectedCustomer !== 'none' ? selectedCustomer : null,
      items: cart.map(({ product_id, name, price, quantity, discount_type: itemDiscountType, discount_value: itemDiscountValue, discount_amount: itemDiscountAmount, discount_reason }) => ({ 
        product_id, 
        product_name: name,
        unit_price: price, 
        quantity,
        subtotal: price * quantity,
        // Rabais par produit
        discount_type: itemDiscountType || null,
        discount_value: itemDiscountValue || 0,
        discount_amount: itemDiscountAmount || 0,
        discount_reason: discount_reason || null,
        final_subtotal: (price * quantity) - (itemDiscountAmount || 0)
      })),
      subtotal: subtotal,
      // Rabais global (manuel)
      discount_type: discountValue ? discountType : null,
      discount_value: discountValue ? parseFloat(discountValue) : 0,
      discount_amount: calculateManualDiscountAmount(),
      // Code promo
      promo_code: promoCodeValidation ? promoCode : null,
      promo_discount_amount: promoCodeValidation?.discount_amount || 0,
      // Rabais automatiques
      automatic_discounts: automaticDiscounts.map(d => ({
        rule_id: d.rule_id,
        rule_name: d.rule_name,
        discount_amount: d.discount_amount
      })),
      automatic_discount_amount: calculateAutomaticDiscountAmount(),
      // Total des rabais
      total_discount_amount: discountAmount,
      total: total,
      // Paiement principal - garder le vrai mode même pour paiement mixte
      payment_method: paymentMethod,
      payment_details: paymentDetailsData,
      amount_paid: amountPaid,
      debt_amount: debtAmountValue,
    };

    // Ajouter les infos du paiement mixte (2 modes)
    if (useMixedPayment && secondPaymentMethod) {
      saleData.is_split_payment = true;
      saleData.split_payments = [
        {
          method: paymentMethod,
          amount: parseFloat(firstPaymentAmount) || 0,
          details: paymentDetailsData
        },
        {
          method: secondPaymentMethod,
          amount: parseFloat(secondPaymentAmount) || 0,
          details: secondPaymentDetailsData
        }
      ];
    }

    if (isOnline) {
      createSale.mutate(saleData, {
        onSuccess: async (newSale) => {
          await addItem('sales', newSale);
          setCart([]);
          setSelectedCustomer('');
          setCustomerSearch('');
          setPaymentMethod('cash');
          setDiscountType('percent');
          setDiscountValue('');
          setUseMixedPayment(false);
          setSecondPaymentMethod('');
          setFirstPaymentAmount('');
          setSecondPaymentAmount('');
          setUseDebtPayment(false);
          setDebtAmount('');
          resetPaymentDetails();
          resetOtpState();
          resetSecondOtpState();
          setProductSearch('');
          // Réinitialiser les nouveaux états de rabais
          setPromoCode('');
          setPromoCodeValidation(null);
          setPromoCodeError('');
          setAutomaticDiscounts([]);
          setShowProductDiscount(null);
          setShowDialog(false);
          if (newSale.has_debt) {
            toast.success(`Vente enregistrée avec ${formatAmount(newSale.debt_amount)} en dette`);
          } else if (newSale.is_split_payment) {
            toast.success('Vente enregistrée avec paiement mixte');
          }
        },
        onError: async (error) => {
          // Si erreur, basculer en mode offline
          console.log('Erreur, passage en mode offline:', error);
          toast.error(error.response?.data?.detail || 'Erreur lors de la vente');
        },
      });
    } else {
      // Mode hors-ligne explicite
      if (useMixedPayment || useDebtPayment || paymentMethod === 'debt') {
        toast.error('Les ventes à crédit et paiements mixtes ne sont pas disponibles hors-ligne');
        return;
      }
      try {
        await createOfflineSale(saleData, products);
        toast.warning('Vente enregistrée localement (hors-ligne)', {
          description: 'Elle sera synchronisée au retour de la connexion',
          icon: <WifiOff className="w-4 h-4" />
        });
        setCart([]);
        setSelectedCustomer('');
        setCustomerSearch('');
        setPaymentMethod('cash');
        setDiscountType('percent');
        setDiscountValue('');
        setUseMixedPayment(false);
        setSecondPaymentMethod('');
        setFirstPaymentAmount('');
        setSecondPaymentAmount('');
        setUseDebtPayment(false);
        setDebtAmount('');
        resetPaymentDetails();
        resetSecondOtpState();
        resetOtpState();
        setProductSearch('');
        setShowDialog(false);
      } catch (offlineError) {
        toast.error('Erreur lors de l\'enregistrement');
      }
    }
  };

  const handleViewDetails = (sale) => {
    setSelectedSale(sale);
    setShowDetailDialog(true);
  };

  // Fonction pour générer et télécharger le PDF de la vente
  const generateSalePDF = (sale) => {
    const customerName = getCustomerName(sale.customer_id);
    const saleDate = new Date(sale.created_at).toLocaleString('fr-FR');
    
    // Générer le label de paiement (simple ou multiple)
    let paymentLabel = '';
    if (sale.is_split_payment && sale.split_payments && sale.split_payments.length > 0) {
      // Paiement multiple - afficher tous les modes avec montants
      paymentLabel = sale.split_payments
        .map(sp => `${getPaymentLabel(sp.method)} (${formatAmount(sp.amount)})`)
        .join(' + ');
    } else {
      paymentLabel = getPaymentLabel(sale.payment_method);
    }
    
    // Section dette si applicable
    let debtSection = '';
    if (sale.has_debt && sale.debt_amount > 0) {
      debtSection = `
        <div class="debt-section">
          <h3>Informations de crédit</h3>
          <div class="debt-grid">
            <div>
              <label>Payé</label>
              <span>${formatAmount(sale.amount_paid || 0)}</span>
            </div>
            <div>
              <label>Restant dû</label>
              <span class="debt-amount">${formatAmount(sale.debt_amount)}</span>
            </div>
          </div>
        </div>
      `;
    }
    
    // Créer le contenu HTML pour le PDF
    const printContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <title>Reçu de vente - ${saleDate}</title>
        <style>
          * { margin: 0; padding: 0; box-sizing: border-box; }
          body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            padding: 40px; 
            max-width: 800px; 
            margin: 0 auto;
            color: #1e293b;
          }
          .header { 
            text-align: center; 
            margin-bottom: 30px; 
            padding-bottom: 20px; 
            border-bottom: 2px solid #0d9488;
          }
          .header h1 { 
            color: #0d9488; 
            font-size: 28px; 
            margin-bottom: 5px;
          }
          .header p { 
            color: #64748b; 
            font-size: 14px;
          }
          .info-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 8px;
          }
          .info-item label { 
            display: block; 
            font-size: 12px; 
            color: #64748b; 
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .info-item span { 
            font-size: 16px; 
            font-weight: 600;
            color: #1e293b;
          }
          .info-item.full-width {
            grid-column: 1 / -1;
          }
          .debt-section {
            margin-bottom: 30px;
            padding: 15px 20px;
            background: #fffbeb;
            border: 1px solid #fcd34d;
            border-radius: 8px;
          }
          .debt-section h3 {
            font-size: 14px;
            color: #92400e;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          .debt-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
          }
          .debt-grid label {
            display: block;
            font-size: 11px;
            color: #b45309;
            margin-bottom: 4px;
            text-transform: uppercase;
          }
          .debt-grid span {
            font-size: 16px;
            font-weight: 600;
            color: #92400e;
          }
          .debt-amount {
            color: #dc2626 !important;
          }
          .items-section { margin-bottom: 30px; }
          .items-section h3 { 
            font-size: 16px; 
            margin-bottom: 15px; 
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.5px;
          }
          table { 
            width: 100%; 
            border-collapse: collapse;
          }
          th { 
            text-align: left; 
            padding: 12px; 
            background: #f1f5f9; 
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #64748b;
            border-bottom: 2px solid #e2e8f0;
          }
          th:last-child { text-align: right; }
          td { 
            padding: 12px; 
            border-bottom: 1px solid #e2e8f0;
            font-size: 14px;
          }
          td:last-child { 
            text-align: right; 
            font-weight: 600;
          }
          .total-row { 
            background: #0d9488; 
            color: white;
          }
          .total-row td { 
            padding: 16px 12px; 
            font-size: 18px; 
            font-weight: 700;
            border: none;
          }
          .footer { 
            text-align: center; 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 1px solid #e2e8f0;
            color: #94a3b8;
            font-size: 12px;
          }
          @media print {
            body { padding: 20px; }
            .no-print { display: none; }
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>${appSettings?.pharmacy_name || 'DynSoft Pharma'}</h1>
          <p>Reçu de vente</p>
        </div>
        
        <div class="info-grid">
          <div class="info-item">
            <label>Date et heure</label>
            <span>${saleDate}</span>
          </div>
          <div class="info-item">
            <label>Client</label>
            <span>${customerName}</span>
          </div>
          <div class="info-item ${sale.is_split_payment ? 'full-width' : ''}">
            <label>Mode de paiement</label>
            <span>${paymentLabel}</span>
          </div>
          ${!sale.is_split_payment ? `
          <div class="info-item">
            <label>Référence</label>
            <span>${sale.sale_number || sale.id?.substring(0, 8).toUpperCase() || 'N/A'}</span>
          </div>
          ` : `
          <div class="info-item">
            <label>Référence</label>
            <span>${sale.sale_number || sale.id?.substring(0, 8).toUpperCase() || 'N/A'}</span>
          </div>
          `}
        </div>
        
        ${debtSection}
        
        <div class="items-section">
          <h3>Articles</h3>
          <table>
            <thead>
              <tr>
                <th>Produit</th>
                <th>Prix unitaire</th>
                <th>Quantité</th>
                <th>Sous-total</th>
              </tr>
            </thead>
            <tbody>
              ${sale.items?.map(item => {
                const itemName = item.product_name || item.name || 'Article';
                const itemPrice = item.unit_price || item.price || 0;
                return `
                <tr>
                  <td>${itemName}</td>
                  <td>${formatAmount(itemPrice)}</td>
                  <td>${item.quantity}</td>
                  <td>${formatAmount(itemPrice * item.quantity)}</td>
                </tr>
              `}).join('') || ''}
              ${sale.tva_total > 0 ? `
              <tr>
                <td colspan="3" style="text-align: right;">Total HT</td>
                <td>${formatAmount(sale.total_ht || sale.total)}</td>
              </tr>
              <tr>
                <td colspan="3" style="text-align: right;">TVA</td>
                <td>${formatAmount(sale.tva_total)}</td>
              </tr>
              ` : ''}
              <tr class="total-row">
                <td colspan="3">TOTAL TTC</td>
                <td>${formatAmount(sale.total || 0)}</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="footer">
          <p>Merci pour votre achat !</p>
          <p style="margin-top: 5px;">Document généré le ${new Date().toLocaleString('fr-FR')}</p>
        </div>
      </body>
      </html>
    `;
    
    // Ouvrir une nouvelle fenêtre et imprimer/sauvegarder en PDF
    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();
    printWindow.focus();
    
    // Attendre le chargement puis lancer l'impression
    setTimeout(() => {
      printWindow.print();
    }, 250);
    
    toast.success('Document PDF généré');
  };

  // Fonction pour ouvrir le dialogue de retour
  const handleReturnClick = async (sale) => {
    setSelectedSale(sale);
    
    try {
      // Vérifier l'éligibilité au retour (délai)
      const eligibilityRes = await api.get(`/returns/check-eligibility/${sale.id}`);
      const eligibility = eligibilityRes.data;
      
      if (!eligibility.is_eligible) {
        toast.error(eligibility.message);
        return;
      }
      
      // Charger les retours existants pour cette vente
      const returnsRes = await api.get(`/returns/sale/${sale.id}`);
      const existingReturns = returnsRes.data;
      
      // Calculer les quantités déjà retournées par produit
      const returnedQuantities = {};
      existingReturns.forEach(ret => {
        ret.items.forEach(item => {
          returnedQuantities[item.product_id] = (returnedQuantities[item.product_id] || 0) + item.quantity;
        });
      });
      
      // Initialiser les articles de retour avec quantité 0
      // Adapter les noms de champs: product_name -> name, unit_price -> price
      const items = sale.items.map(item => ({
        product_id: item.product_id,
        name: item.product_name || item.name,
        price: item.unit_price || item.price || 0,
        sold_quantity: item.quantity,
        returned_quantity: returnedQuantities[item.product_id] || 0,
        return_quantity: 0
      }));
      
      setReturnItems(items);
      setReturnReason('');
      setShowReturnDialog(true);
      
      // Afficher un message informatif sur le délai restant
      if (eligibility.days_remaining <= 1) {
        toast.warning(`Attention: ${eligibility.days_remaining} jour(s) restant(s) pour effectuer un retour`);
      }
    } catch (error) {
      console.error('Error checking return eligibility:', error);
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la vérification';
      toast.error(errorMessage);
    }
  };

  // Mettre à jour la quantité de retour
  const updateReturnQuantity = (productId, quantity) => {
    setReturnItems(returnItems.map(item => {
      if (item.product_id === productId) {
        const maxReturn = item.sold_quantity - item.returned_quantity;
        const newQty = Math.max(0, Math.min(parseInt(quantity) || 0, maxReturn));
        return { ...item, return_quantity: newQty };
      }
      return item;
    }));
  };

  // Calculer le total du remboursement
  const calculateRefundTotal = () => {
    return returnItems.reduce((sum, item) => sum + (item.price * item.return_quantity), 0);
  };

  // Soumettre le retour
  const handleReturnSubmit = async () => {
    const itemsToReturn = returnItems.filter(item => item.return_quantity > 0);
    
    if (itemsToReturn.length === 0) {
      toast.error('Veuillez sélectionner au moins un article à retourner');
      return;
    }

    if (!returnReason.trim()) {
      toast.error('Le motif du retour est obligatoire');
      return;
    }
    
    createReturn.mutate(
      {
        sale_id: selectedSale.id,
        items: itemsToReturn.map(item => ({
          product_id: item.product_id,
          quantity: item.return_quantity
        })),
        reason: returnReason.trim()
      },
      {
        onSuccess: () => {
          setShowReturnDialog(false);
          setSelectedSale(null);
        },
      }
    );
  };

  // Charger l'historique des opérations
  const loadOperationsHistory = async () => {
    try {
      await refetchHistory();
    } catch (error) {
      console.error('Error loading history:', error);
    }
    // Toujours ouvrir le dialog même si le refetch échoue
    setShowHistoryDialog(true);
  };

  const getCustomerName = (customerId) => {
    if (!customerId) return 'Client anonyme';
    const customer = customers.find(c => c.id === customerId);
    return customer?.name || 'Client inconnu';
  };

  // Mapping des icônes lucide-react par nom
  const iconMap = {
    'banknote': Banknote,
    'credit-card': CreditCard,
    'smartphone': Smartphone,
    'file-check': FileCheck,
    'wallet': Wallet,
    'circle-dollar-sign': CircleDollarSign,
  };

  const getPaymentIcon = (methodCode) => {
    // D'abord chercher dans les méthodes chargées depuis l'API
    const method = paymentMethods.find(m => m.code === methodCode);
    if (method && method.icon) {
      const IconComponent = iconMap[method.icon] || Banknote;
      return <IconComponent className="w-4 h-4" />;
    }
    // Fallback pour rétro-compatibilité
    switch (methodCode) {
      case 'card': return <CreditCard className="w-4 h-4" />;
      case 'check': return <FileCheck className="w-4 h-4" />;
      case 'orange_money': return <Smartphone className="w-4 h-4" />;
      case 'mtn_money': return <Smartphone className="w-4 h-4" />;
      default: return <Banknote className="w-4 h-4" />;
    }
  };

  const getPaymentLabel = (methodCode) => {
    // D'abord chercher dans les méthodes chargées depuis l'API
    const method = paymentMethods.find(m => m.code === methodCode);
    if (method) {
      return method.name;
    }
    // Fallback pour rétro-compatibilité
    switch (methodCode) {
      case 'card': return 'Carte bancaire';
      case 'check': return 'Chèque';
      case 'orange_money': return 'Orange Money';
      case 'mtn_money': return 'MTN Money';
      default: return 'Espèces';
    }
  };

  // Obtenir les styles du badge agent selon le rôle
  const getAgentBadgeStyles = (role) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800 border border-purple-200';
      case 'pharmacien':
        return 'bg-teal-100 text-teal-800 border border-teal-200';
      case 'caissier':
        return 'bg-amber-100 text-amber-800 border border-amber-200';
      case 'migrated':
        return 'bg-blue-50 text-blue-600 border border-blue-200';
      default:
        return 'bg-slate-100 text-slate-600 border border-slate-200';
    }
  };

  // Filtrer les produits : uniquement actifs et correspondant à la recherche
  const filteredProducts = products.filter((p) => {
    // Exclure les produits désactivés
    if (p.is_active === false) return false;
    
    const searchLower = productSearch.toLowerCase();
    return p.name?.toLowerCase().includes(searchLower) || 
           p.barcode?.toLowerCase().includes(searchLower);
  });

  // Handle barcode scan
  const handleBarcodeScan = (barcode) => {
    const product = products.find(p => p.barcode === barcode);
    if (product) {
      if (product.stock <= 0) {
        toast.error(`${product.name} est en rupture de stock`);
      } else {
        addToCart(product);
        toast.success(`${product.name} ajouté au panier`);
      }
    } else {
      toast.error(`Aucun produit trouvé avec le code-barres: ${barcode}`);
    }
    setShowBarcodeScanner(false);
  };

  const filteredCustomers = customers
    .filter((c) => c.is_active !== false) // Exclure les clients inactifs
    .filter((c) =>
      c.name?.toLowerCase().includes(customerSearch.toLowerCase()) ||
      c.phone?.includes(customerSearch)
    );

  // Les ventes sont déjà filtrées côté serveur via l'API
  const filteredSales = sales;

  // Loading state avec skeleton shimmer
  if (salesLoading && sales.length === 0) {
    return (
      <Layout>
        <SkeletonSalesPage />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="sales-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-4xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Ventes
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des ventes et facturation
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            {/* Bouton Ventes en attente avec badge */}
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                if (!isWithinScheduledHours) {
                  toast.error('Accès restreint', {
                    description: shiftEligibility?.reason || 'Vous êtes hors de vos horaires de travail'
                  });
                  return;
                }
                setShowPendingSalesDialog(true);
              }}
              className={`rounded-full relative ${!isWithinScheduledHours ? 'opacity-50 cursor-not-allowed' : ''}`}
              data-testid="pending-sales-button"
              title={!isWithinScheduledHours ? (shiftEligibility?.reason || 'Hors horaires de travail') : ''}
            >
              <Pause className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
              <span className="hidden sm:inline">En attente</span>
              {pendingSalesCount?.count > 0 && (
                <span className="absolute -top-2 -right-2 bg-amber-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
                  {pendingSalesCount.count}
                </span>
              )}
            </Button>
            <Button 
              variant="outline"
              size="sm"
              onClick={() => {
                if (!isWithinScheduledHours) {
                  toast.error('Accès restreint', {
                    description: shiftEligibility?.reason || 'Vous êtes hors de vos horaires de travail'
                  });
                  return;
                }
                setShowHistoryDialog(true);
              }}
              data-testid="history-button"
              className={`rounded-full ${!isWithinScheduledHours ? 'opacity-50 cursor-not-allowed' : ''}`}
              title={!isWithinScheduledHours ? (shiftEligibility?.reason || 'Hors horaires de travail') : ''}
            >
              <History className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
              <span className="hidden sm:inline">Historique</span>
            </Button>
            <Dialog open={showDialog} onOpenChange={setShowDialog}>
              <DialogTrigger asChild>
                <Button 
                  data-testid="new-sale-button" 
                  size="sm"
                  className="bg-teal-700 hover:bg-teal-800 rounded-full"
                  disabled={!canOperate}
                  title={!canOperate ? shiftBlockReason : ""}
                >
                  <Plus className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Nouvelle vente</span>
                  <span className="sm:hidden">Vente</span>
                </Button>
              </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Nouvelle vente</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6" data-testid="sale-form">
                <div className="grid grid-cols-2 gap-4">
                  {/* Client Search */}
                  <div className="relative">
                    <Label htmlFor="customer">Client (optionnel)</Label>
                    <div className="relative mt-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" strokeWidth={1.5} />
                      <Input
                        placeholder="Rechercher un client par nom ou téléphone..."
                        value={customerSearch}
                        onChange={(e) => {
                          setCustomerSearch(e.target.value);
                          setShowCustomerDropdown(true);
                          if (!e.target.value) {
                            setSelectedCustomer('');
                          }
                        }}
                        onFocus={() => setShowCustomerDropdown(true)}
                        data-testid="customer-search-input"
                        className="pl-9"
                      />
                    </div>
                    {showCustomerDropdown && customerSearch && filteredCustomers.length > 0 && (
                      <div className="absolute z-50 w-full mt-1 max-h-48 overflow-y-auto bg-white border border-slate-200 rounded-lg shadow-lg">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedCustomer('');
                            setCustomerSearch('');
                            setShowCustomerDropdown(false);
                          }}
                          className="w-full text-left px-4 py-2 hover:bg-slate-50 text-slate-500 border-b border-slate-100"
                        >
                          Aucun client (vente anonyme)
                        </button>
                        {filteredCustomers.map((customer) => (
                          <button
                            key={customer.id}
                            type="button"
                            onClick={() => {
                              setSelectedCustomer(customer.id);
                              setCustomerSearch(customer.name);
                              setShowCustomerDropdown(false);
                            }}
                            data-testid={`select-customer-${customer.id}`}
                            className="w-full text-left px-4 py-2 hover:bg-slate-50 transition-colors"
                          >
                            <p className="font-medium text-slate-900">{customer.name}</p>
                            {customer.phone && (
                              <p className="text-sm text-slate-500">{customer.phone}</p>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                    {selectedCustomer && (
                      <p className="mt-1 text-sm text-teal-600">
                        ✓ Client sélectionné: {customers.find(c => c.id === selectedCustomer)?.name}
                      </p>
                    )}
                  </div>
                  <div>
                    <Label htmlFor="payment">Mode de paiement</Label>
                    <Select value={paymentMethod} onValueChange={(value) => {
                      setPaymentMethod(value);
                      resetPaymentDetails(); // Réinitialiser les détails lors du changement
                    }}>
                      <SelectTrigger data-testid="payment-select" className="mt-1">
                        <SelectValue placeholder="Sélectionner un mode de paiement" />
                      </SelectTrigger>
                      <SelectContent>
                        {paymentMethodsLoading ? (
                          <SelectItem value="loading" disabled>Chargement...</SelectItem>
                        ) : paymentMethods.length === 0 ? (
                          <SelectItem value="cash">Espèces</SelectItem>
                        ) : (
                          paymentMethods
                            .filter(method => !method.admin_only || user?.role === 'admin')
                            .map((method) => (
                            <SelectItem key={method.code} value={method.code}>
                              <div className="flex items-center gap-2">
                                {getPaymentIcon(method.code)}
                                {method.name}
                              </div>
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Champs conditionnels selon le mode de paiement - RENDU DYNAMIQUE */}
                {(() => {
                  const selectedMethod = paymentMethods.find(m => m.code === paymentMethod);
                  if (!selectedMethod || !selectedMethod.required_fields || selectedMethod.required_fields.length === 0) {
                    return null;
                  }
                  
                  // Mapping des couleurs pour les différents modes
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
                  const gridCols = selectedMethod.required_fields.length === 2 ? 'grid-cols-2' : 'grid-cols-3';
                  
                  return (
                    <div className={`p-4 ${colors.bg} rounded-lg border ${colors.border} space-y-3`}>
                      <div className={`flex items-center gap-2 ${colors.text} mb-2`}>
                        {getPaymentIcon(selectedMethod.code)}
                        <span className="text-sm font-medium">Détails {selectedMethod.name}</span>
                      </div>
                      <div className={`grid ${gridCols} gap-3`}>
                        {selectedMethod.required_fields.map((field) => (
                          <div key={field.name}>
                            <Label className={`text-sm ${colors.label}`}>
                              {field.label} {field.required && <span className="text-red-500">*</span>}
                            </Label>
                            <Input
                              type={field.type || 'text'}
                              maxLength={field.maxLength}
                              value={paymentDetails[`${paymentMethod}_${field.name}`] || ''}
                              onChange={(e) => {
                                let value = e.target.value;
                                // Traitement spécial pour les champs numériques (4 derniers chiffres)
                                if (field.maxLength && field.type !== 'tel') {
                                  value = value.replace(/\D/g, '').slice(0, field.maxLength);
                                }
                                setPaymentDetails({
                                  ...paymentDetails,
                                  [`${paymentMethod}_${field.name}`]: value
                                });
                              }}
                              placeholder={field.placeholder || ''}
                              className="mt-1 bg-white"
                              data-testid={`payment-field-${field.name}`}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}

                {/* Section OTP pour Mobile Money (Orange Money / MTN Money) */}
                {/* Section OTP Mobile Money - En cours de développement */}
                {isMobileMoneyPayment && (
                  <div className={`p-4 rounded-lg border space-y-4 ${
                    paymentMethod === 'orange_money' 
                      ? 'bg-orange-50 border-orange-200' 
                      : 'bg-yellow-50 border-yellow-200'
                  }`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Shield className={`w-4 h-4 ${paymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`} />
                        <span className={`text-sm font-medium ${paymentMethod === 'orange_money' ? 'text-orange-700' : 'text-yellow-700'}`}>
                          Vérification OTP
                        </span>
                      </div>
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
                        <Clock className="w-3 h-3" />
                        En cours de développement
                      </span>
                    </div>

                    <div className="space-y-2">
                      {cart.length === 0 && (
                        <p className="text-sm text-red-600 font-medium">
                          ⚠️ Ajoutez au moins un produit au panier avant de demander le code OTP
                        </p>
                      )}
                      <p className={`text-sm ${paymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`}>
                        Un code de vérification sera envoyé au numéro: <strong>{getDefaultOtpPhone() || 'Non configuré dans Paramètres'}</strong>
                      </p>
                      <Button
                        type="button"
                        disabled={true}
                        className={`w-full ${
                          paymentMethod === 'orange_money' 
                            ? 'bg-orange-400 cursor-not-allowed' 
                            : 'bg-yellow-400 cursor-not-allowed'
                        } text-white`}
                        data-testid="request-otp-btn"
                      >
                        <Send className="w-4 h-4 mr-2" />
                        Demander le code OTP
                      </Button>
                    </div>
                  </div>
                )}
                    {/* Champs Mobile Money supprimés - maintenant dans la section dynamique */}

                {/* Section Paiement Mixte (2 modes de paiement) - visible si au moins 1 produit */}
                {paymentMethod !== 'debt' && cart.length > 0 && (
                  <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-indigo-700">
                        <CircleDollarSign className="w-4 h-4" />
                        <span className="text-sm font-medium">Paiement Mixte (2 modes)</span>
                      </div>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={useMixedPayment}
                          onChange={(e) => {
                            setUseMixedPayment(e.target.checked);
                            if (!e.target.checked) {
                              setSecondPaymentMethod('');
                              setFirstPaymentAmount('');
                              setSecondPaymentAmount('');
                              resetSecondOtpState();
                            } else {
                              // Pré-remplir le premier montant à 50% du total
                              setFirstPaymentAmount(Math.round(calculateTotal() / 2).toString());
                            }
                          }}
                          className="w-4 h-4 rounded border-indigo-300 text-indigo-600 focus:ring-indigo-500"
                        />
                        <span className="text-sm text-indigo-700">Activer</span>
                      </label>
                    </div>
                    
                    {useMixedPayment && (
                      <div className="space-y-4">
                        <p className="text-xs text-indigo-600">
                          Divisez le paiement entre 2 modes différents
                        </p>
                        
                        {/* Premier mode de paiement */}
                        <div className="p-3 bg-white rounded-lg border border-indigo-100">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-medium">1</span>
                            <span className="text-sm font-medium text-slate-700">
                              {paymentMethods.find(m => m.code === paymentMethod)?.name || 'Premier mode'}
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Input
                              type="number"
                              min="0"
                              max={calculateTotal()}
                              value={firstPaymentAmount}
                              onChange={(e) => setFirstPaymentAmount(e.target.value)}
                              placeholder="Montant"
                              className="flex-1"
                            />
                            <span className="text-sm text-slate-500 whitespace-nowrap">GNF</span>
                          </div>
                        </div>

                        {/* Second mode de paiement */}
                        <div className="p-3 bg-white rounded-lg border border-indigo-100">
                          <div className="flex items-center gap-2 mb-2">
                            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center font-medium">2</span>
                            <span className="text-sm font-medium text-slate-700">Second mode</span>
                          </div>
                          <Select
                            value={secondPaymentMethod}
                            onValueChange={(value) => setSecondPaymentMethod(value)}
                          >
                            <SelectTrigger className="mb-2">
                              <SelectValue placeholder="Choisir le second mode" />
                            </SelectTrigger>
                            <SelectContent>
                              {paymentMethods
                                .filter(m => m.code !== paymentMethod)
                                .filter(method => !method.admin_only || user?.role === 'admin')
                                .map((method) => (
                                  <SelectItem key={method.code} value={method.code}>
                                    <div className="flex items-center gap-2">
                                      {getPaymentIcon(method.code)}
                                      {method.name}
                                    </div>
                                  </SelectItem>
                                ))}
                            </SelectContent>
                          </Select>
                          
                          {secondPaymentMethod && (
                            <div className="flex items-center gap-2">
                              <Input
                                type="number"
                                min="0"
                                value={secondPaymentAmount}
                                readOnly
                                className="flex-1 bg-slate-50"
                              />
                              <span className="text-sm text-slate-500 whitespace-nowrap">GNF</span>
                            </div>
                          )}
                        </div>

                        {/* Champs spécifiques au second mode de paiement */}
                        {secondPaymentMethod && (() => {
                          const method = paymentMethods.find(m => m.code === secondPaymentMethod);
                          if (!method || !method.required_fields || method.required_fields.length === 0) return null;
                          
                          return (
                            <div className="p-3 bg-slate-50 rounded-lg space-y-2">
                              <p className="text-xs font-medium text-slate-600">
                                Détails {method.name}
                              </p>
                              {method.required_fields.map((field) => (
                                <div key={field.name}>
                                  <Label className="text-xs text-slate-600">{field.label}</Label>
                                  <Input
                                    type={field.type}
                                    maxLength={field.maxLength}
                                    value={secondPaymentDetails[`${secondPaymentMethod}_${field.name}`] || ''}
                                    onChange={(e) => setSecondPaymentDetails(prev => ({
                                      ...prev,
                                      [`${secondPaymentMethod}_${field.name}`]: e.target.value
                                    }))}
                                    placeholder={field.placeholder}
                                    className="mt-1 text-sm"
                                  />
                                </div>
                              ))}
                            </div>
                          );
                        })()}

                        {/* Section OTP pour le second mode Mobile Money - En cours de développement */}
                        {isSecondMobileMoneyPayment && secondPaymentMethod && (
                          <div className={`p-3 rounded-lg border space-y-2 ${
                            secondPaymentMethod === 'orange_money' 
                              ? 'bg-orange-50 border-orange-200' 
                              : 'bg-yellow-50 border-yellow-200'
                          }`}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-2">
                                <Shield className={`w-4 h-4 ${secondPaymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`} />
                                <span className={`text-xs font-medium ${secondPaymentMethod === 'orange_money' ? 'text-orange-700' : 'text-yellow-700'}`}>
                                  Vérification OTP
                                </span>
                              </div>
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
                                <Clock className="w-3 h-3" />
                                En cours de développement
                              </span>
                            </div>
                            <p className={`text-xs ${secondPaymentMethod === 'orange_money' ? 'text-orange-600' : 'text-yellow-600'}`}>
                              Code envoyé au: <strong>{getDefaultOtpPhone(secondPaymentMethod) || 'Non configuré'}</strong>
                            </p>
                            <Button
                              type="button"
                              size="sm"
                              disabled={true}
                              className={`w-full text-xs ${
                                secondPaymentMethod === 'orange_money' 
                                  ? 'bg-orange-400 cursor-not-allowed' 
                                  : 'bg-yellow-400 cursor-not-allowed'
                              } text-white`}
                            >
                              <Send className="w-3 h-3 mr-1" />
                              Demander OTP
                            </Button>
                          </div>
                        )}

                        {/* Résumé du paiement mixte */}
                        {secondPaymentMethod && (
                          <div className="p-3 bg-indigo-100 rounded-lg">
                            <p className="text-xs font-medium text-indigo-800 mb-2">Résumé du paiement</p>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between text-indigo-700">
                                <span>{paymentMethods.find(m => m.code === paymentMethod)?.name}:</span>
                                <span className="font-medium">{formatAmount(parseFloat(firstPaymentAmount) || 0)}</span>
                              </div>
                              <div className="flex justify-between text-indigo-700">
                                <span>{paymentMethods.find(m => m.code === secondPaymentMethod)?.name}:</span>
                                <span className="font-medium">{formatAmount(parseFloat(secondPaymentAmount) || 0)}</span>
                              </div>
                              <div className="flex justify-between text-indigo-900 font-semibold border-t border-indigo-200 pt-1 mt-1">
                                <span>Total:</span>
                                <span>{formatAmount((parseFloat(firstPaymentAmount) || 0) + (parseFloat(secondPaymentAmount) || 0))}</span>
                              </div>
                              {Math.abs((parseFloat(firstPaymentAmount) || 0) + (parseFloat(secondPaymentAmount) || 0) - calculateTotal()) > 0.01 && (
                                <p className="text-xs text-red-600 mt-1">
                                  ⚠️ Le total ne correspond pas au montant de la vente ({formatAmount(calculateTotal())})
                                </p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Alerte si mode Dette sélectionné */}
                {paymentMethod === 'debt' && (
                  <div className="p-4 bg-red-50 rounded-lg border border-red-200 space-y-2">
                    <div className="flex items-center gap-2 text-red-700">
                      <Wallet className="w-4 h-4" />
                      <span className="text-sm font-medium">Vente 100% à crédit</span>
                    </div>
                    {!selectedCustomer || selectedCustomer === 'none' ? (
                      <p className="text-sm text-red-600">⚠️ Veuillez sélectionner un client</p>
                    ) : creditLoading ? (
                      <div className="flex items-center gap-2 text-sm text-red-600">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Vérification du crédit...
                      </div>
                    ) : customerCredit ? (
                      <div className="text-sm space-y-1">
                        <div className="flex justify-between text-red-700">
                          <span>Crédit disponible:</span>
                          <span className="font-semibold">{formatAmount(customerCredit.available_credit)}</span>
                        </div>
                        {calculateTotal() > customerCredit.available_credit && (
                          <p className="text-red-600 font-medium">⚠️ Montant dépasse le crédit disponible!</p>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm text-red-600">⚠️ Client non autorisé au crédit</p>
                    )}
                  </div>
                )}

                {/* Product Search */}
                <div>
                  <Label>Rechercher un produit (par nom ou code-barres)</Label>
                  <div className="relative mt-2 flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
                      <Input
                        placeholder="Rechercher par nom ou code-barres..."
                        value={productSearch}
                        onChange={(e) => setProductSearch(e.target.value)}
                        data-testid="product-search-input"
                        className="pl-10"
                      />
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setShowBarcodeScanner(true)}
                      className="shrink-0 border-teal-200 text-teal-700 hover:bg-teal-50 hover:border-teal-300"
                      title="Scanner un code-barres"
                    >
                      <ScanLine className="w-5 h-5" />
                    </Button>
                  </div>
                  {productSearch && filteredProducts.length > 0 && (
                    <div className="mt-2 max-h-48 overflow-y-auto border border-slate-200 rounded-lg">
                      {filteredProducts.slice(0, 8).map((product) => (
                        <button
                          key={product.id}
                          type="button"
                          onClick={() => addToCart(product)}
                          disabled={product.stock <= 0}
                          data-testid={`add-to-cart-${product.id}`}
                          className={`w-full text-left px-4 py-2 transition-colors flex justify-between items-center ${
                            product.stock <= 0 ? 'bg-slate-100 cursor-not-allowed' : 'hover:bg-slate-50'
                          }`}
                        >
                          <div>
                            <p className="font-medium text-slate-900">{product.name}</p>
                            <p className="text-xs text-slate-400">{product.barcode || 'Pas de code-barres'}</p>
                            <p className={`text-sm ${product.stock <= 0 ? 'text-red-500' : 'text-slate-500'}`}>
                              Stock: {product.stock} {product.stock <= 0 && '(Rupture)'}
                            </p>
                          </div>
                          <p className="font-medium text-teal-700">{formatAmount(product.price)}</p>
                        </button>
                      ))}
                    </div>
                  )}
                  {productSearch && filteredProducts.length === 0 && (
                    <p className="mt-2 text-sm text-slate-500">Aucun produit trouvé pour &quot;{productSearch}&quot;</p>
                  )}
                </div>

                {/* Cart */}
                <div>
                  <Label>Panier ({cart.length} article{cart.length > 1 ? 's' : ''})</Label>
                  <div className="mt-2 space-y-2" data-testid="cart-items">
                    {cart.length === 0 ? (
                      <p className="text-slate-500 text-center py-4">Le panier est vide</p>
                    ) : (
                      cart.map((item, index) => (
                        <div key={item.product_id} className="p-3 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="flex-1">
                              <p className="font-medium text-slate-900">{item.name}</p>
                              <p className="text-sm text-slate-500">{formatAmount(item.price)} / unité</p>
                            </div>
                            <Input
                              type="number"
                              min="1"
                              max={item.max_stock}
                              value={item.quantity}
                              onChange={(e) => updateQuantity(item.product_id, e.target.value)}
                              className="w-20"
                              data-testid={`quantity-${item.product_id}`}
                            />
                            <p className="font-medium text-slate-900 w-24 text-right">
                              {formatAmount(item.price * item.quantity)}
                            </p>
                            <button
                              type="button"
                              onClick={() => setShowProductDiscount(showProductDiscount === index ? null : index)}
                              className={`p-1.5 rounded hover:bg-slate-200 ${item.discount_amount ? 'text-green-600' : 'text-slate-400'}`}
                              title="Appliquer un rabais"
                            >
                              <Tag className="w-4 h-4" />
                            </button>
                            <button
                              type="button"
                              onClick={() => removeFromCart(item.product_id)}
                              data-testid={`remove-${item.product_id}`}
                              className="text-red-600 hover:text-red-700"
                            >
                              <X className="w-5 h-5" strokeWidth={1.5} />
                            </button>
                          </div>
                          
                          {/* Rabais par produit - Formulaire */}
                          {showProductDiscount === index && (
                            <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200">
                              <ProductDiscountForm
                                item={item}
                                onApply={(type, value, reason) => applyProductDiscount(item.product_id, type, value, reason)}
                                onCancel={() => setShowProductDiscount(null)}
                              />
                            </div>
                          )}
                          
                          {/* Affichage du rabais appliqué */}
                          {item.discount_amount > 0 && showProductDiscount !== index && (
                            <div className="mt-2 flex items-center justify-between text-sm">
                              <span className="text-green-600 flex items-center gap-1">
                                <Tag className="w-3 h-3" />
                                Rabais: -{item.discount_type === 'percent' ? `${item.discount_value}%` : formatAmount(item.discount_value)}
                                {item.discount_reason && <span className="text-slate-500">({item.discount_reason})</span>}
                              </span>
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-green-700">-{formatAmount(item.discount_amount)}</span>
                                <button
                                  type="button"
                                  onClick={() => removeProductDiscount(item.product_id)}
                                  className="text-red-400 hover:text-red-600"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Rabais */}
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="flex items-center justify-between mb-3">
                    <Label className="text-sm font-medium text-amber-800">Rabais Manuel</Label>
                    <div className="flex gap-1 bg-amber-100 rounded-lg p-0.5">
                      <button
                        type="button"
                        onClick={() => setDiscountType('percent')}
                        className={`px-2 py-1 text-xs rounded-md transition-colors ${
                          discountType === 'percent' 
                            ? 'bg-white text-amber-800 shadow-sm' 
                            : 'text-amber-600 hover:text-amber-800'
                        }`}
                      >
                        <Percent className="w-3 h-3 inline mr-1" />
                        %
                      </button>
                      <button
                        type="button"
                        onClick={() => setDiscountType('amount')}
                        className={`px-2 py-1 text-xs rounded-md transition-colors ${
                          discountType === 'amount' 
                            ? 'bg-white text-amber-800 shadow-sm' 
                            : 'text-amber-600 hover:text-amber-800'
                        }`}
                      >
                        <DollarSign className="w-3 h-3 inline mr-1" />
                        Montant
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Input
                      type="number"
                      min="0"
                      max={discountType === 'percent' ? 100 : undefined}
                      step={discountType === 'percent' ? 1 : 100}
                      value={discountValue}
                      onChange={(e) => setDiscountValue(e.target.value)}
                      placeholder={discountType === 'percent' ? '0' : '0'}
                      className="w-32 bg-white"
                    />
                    <span className="text-sm text-amber-700">
                      {discountType === 'percent' ? '%' : appSettings?.currency || 'GNF'}
                    </span>
                    {calculateManualDiscountAmount() > 0 && (
                      <span className="ml-auto text-sm font-medium text-amber-800">
                        - {formatAmount(calculateManualDiscountAmount())}
                      </span>
                    )}
                  </div>
                  {discountType === 'percent' && parseFloat(discountValue) > 100 && (
                    <p className="text-xs text-red-600 mt-1">Le pourcentage ne peut pas dépasser 100%</p>
                  )}
                </div>

                {/* Code Promo */}
                <div className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <div className="flex items-center gap-2 mb-3">
                    <Tag className="w-4 h-4 text-purple-600" />
                    <Label className="text-sm font-medium text-purple-800">Code Promo</Label>
                  </div>
                  <div className="flex items-center gap-2">
                    <Input
                      value={promoCode}
                      onChange={(e) => {
                        setPromoCode(e.target.value.toUpperCase());
                        setPromoCodeValidation(null);
                        setPromoCodeError('');
                      }}
                      placeholder="PROMO2026"
                      className="flex-1 bg-white font-mono uppercase"
                      disabled={!!promoCodeValidation}
                    />
                    {promoCodeValidation ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={removePromoCode}
                        className="text-red-500 hover:text-red-700"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    ) : (
                      <Button
                        type="button"
                        size="sm"
                        onClick={validatePromoCode}
                        disabled={promoCodeLoading || !promoCode.trim()}
                        className="bg-purple-600 hover:bg-purple-700"
                      >
                        {promoCodeLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          'Valider'
                        )}
                      </Button>
                    )}
                  </div>
                  {promoCodeValidation && (
                    <div className="mt-2 p-2 bg-green-100 rounded-md flex items-center gap-2">
                      <CheckCircle className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-green-700">
                        {promoCodeValidation.promo_code?.name}: -{formatAmount(promoCodeValidation.discount_amount)}
                      </span>
                    </div>
                  )}
                  {promoCodeError && (
                    <p className="text-xs text-red-600 mt-1">{promoCodeError}</p>
                  )}
                </div>

                {/* Rabais Automatiques */}
                {(automaticDiscounts.length > 0 || automaticDiscountsLoading) && (
                  <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-2 mb-2">
                      {automaticDiscountsLoading ? (
                        <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4 text-blue-600" />
                      )}
                      <Label className="text-sm font-medium text-blue-800">
                        Rabais Automatiques
                        {automaticDiscountsLoading && <span className="ml-2 text-blue-600">(calcul en cours...)</span>}
                      </Label>
                    </div>
                    {automaticDiscounts.length > 0 && (
                      <div className="space-y-1">
                        {automaticDiscounts.map((discount, idx) => (
                          <div key={idx} className="flex items-center justify-between text-sm">
                            <span className="text-blue-700">{discount.rule_name}</span>
                            <span className="font-medium text-blue-800">-{formatAmount(discount.discount_amount)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Sous-total et Total */}
                <div className="space-y-2">
                  {/* Toujours afficher le sous-total si le panier n'est pas vide */}
                  {cart.length > 0 && (
                    <div className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                      <span className="text-sm text-slate-600">Sous-total:</span>
                      <span className="text-sm text-slate-600">
                        {formatAmount(calculateSubtotal())}
                      </span>
                    </div>
                  )}
                  
                  {/* Détail des rabais */}
                  {calculateDiscountAmount() > 0 && (
                    <div className="p-3 bg-green-50 rounded-lg border border-green-200 space-y-1">
                      {calculateProductDiscounts() > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-green-600">Rabais produits:</span>
                          <span className="text-green-700 font-medium">-{formatAmount(calculateProductDiscounts())}</span>
                        </div>
                      )}
                      {calculateAutomaticDiscountAmount() > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-green-600">Rabais automatiques:</span>
                          <span className="text-green-700 font-medium">-{formatAmount(calculateAutomaticDiscountAmount())}</span>
                        </div>
                      )}
                      {promoCodeValidation?.discount_amount > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-green-600">Code promo ({promoCode}):</span>
                          <span className="text-green-700 font-medium">-{formatAmount(promoCodeValidation.discount_amount)}</span>
                        </div>
                      )}
                      {calculateManualDiscountAmount() > 0 && (
                        <div className="flex justify-between items-center text-sm">
                          <span className="text-green-600">Rabais manuel:</span>
                          <span className="text-green-700 font-medium">-{formatAmount(calculateManualDiscountAmount())}</span>
                        </div>
                      )}
                      <div className="flex justify-between items-center text-sm pt-1 border-t border-green-200">
                        <span className="text-green-700 font-medium">Total rabais:</span>
                        <span className="text-green-800 font-bold">-{formatAmount(calculateDiscountAmount())}</span>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center p-4 bg-teal-50 rounded-lg">
                    <span className="text-lg font-semibold text-slate-900">Total:</span>
                    <span className="text-2xl font-bold text-teal-700" data-testid="cart-total">
                      {formatAmount(calculateTotal())}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-3">
                  <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                    Annuler
                  </Button>
                  <Button 
                    type="button"
                    variant="outline"
                    onClick={handlePutOnHold}
                    disabled={cart.length === 0 || createPendingSale.isPending}
                    className="border-amber-400 text-amber-600 hover:bg-amber-50"
                    data-testid="put-on-hold-button"
                  >
                    {createPendingSale.isPending ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Pause className="w-4 h-4 mr-2" />
                    )}
                    Mettre en attente
                  </Button>
                  <Button 
                    type="submit" 
                    data-testid="sale-submit-button" 
                    className="bg-teal-700 hover:bg-teal-800"
                    disabled={cart.length === 0}
                  >
                    Valider la vente
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
          </div>
        </div>

        {/* Search */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
            <Input
              placeholder="Rechercher par N° vente, client, agent..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="sales-search-input"
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          <div className="relative w-full sm:w-48">
            <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" strokeWidth={1.5} />
            <Input
              type="date"
              value={searchDate}
              onChange={(e) => setSearchDate(e.target.value)}
              className="pl-10"
              placeholder="Date"
              disabled={!isWithinScheduledHours}
            />
          </div>
          {(searchQuery || searchDate) && (
            <Button 
              variant="outline" 
              onClick={() => { setSearchQuery(''); setSearchDate(''); }}
              className="whitespace-nowrap"
            >
              <X className="w-4 h-4 mr-1" />
              Effacer
            </Button>
          )}
        </div>

        {/* Message de restriction pour utilisateurs hors horaires */}
        {!isWithinScheduledHours && (
          <div className="p-6 bg-amber-50 rounded-xl border border-amber-200">
            <div className="flex items-start gap-4">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Timer className="w-6 h-6 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-800">Accès restreint - Hors horaires de travail</h3>
                <p className="text-sm text-amber-700 mt-1">
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder à l\'historique des ventes en dehors de vos horaires planifiés.'}
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
        )}

        {/* Sales List - Masqué si hors horaires */}
        {isWithinScheduledHours && (
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    N° Vente
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Date
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Agent
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Client
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Articles
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Paiement
                  </th>
                  <th className="px-6 py-4 text-right text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Total
                  </th>
                  <th className="px-6 py-4 text-center text-sm font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredSales.map((sale) => (
                  <tr 
                    key={sale.id} 
                    className={`hover:bg-slate-50 transition-colors ${sale._offline && !sale._synced ? 'bg-amber-50/50' : ''}`} 
                    data-testid={`sale-row-${sale.id}`}
                  >
                    <td className="px-6 py-4 text-sm">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-teal-700 bg-teal-50 px-2 py-1 rounded">
                          {sale.sale_number || `VNT-${sale.id?.substring(0, 8).toUpperCase()}`}
                        </span>
                        {sale._offline && !sale._synced && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 text-xs" title="En attente de synchronisation">
                            <CloudOff className="w-3 h-3" />
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {new Date(sale.created_at).toLocaleString('fr-FR')}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      <span 
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${getAgentBadgeStyles(sale.user_role)}`}
                        title={sale.user_name || 'Inconnu'}
                      >
                        {sale.employee_code || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {getCustomerName(sale.customer_id)}
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-900">
                      {sale.items?.length || 0} article(s)
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
                      {sale.is_split_payment && sale.split_payments ? (
                        <div className="space-y-1">
                          {sale.split_payments.map((sp, idx) => (
                            <div key={idx} className="flex items-center gap-2 text-xs">
                              {getPaymentIcon(sp.method)}
                              <span>{getPaymentLabel(sp.method)}</span>
                              <span className="text-slate-400">({formatAmount(sp.amount)})</span>
                            </div>
                          ))}
                          {(sale.discount_amount || sale.discount) > 0 && (
                            <div className="flex items-center gap-1.5 text-xs mt-1 pt-1 border-t border-slate-200">
                              <Tag className="w-3 h-3 text-green-600" />
                              <span className="text-green-600 font-medium">
                                Rabais: -{formatAmount(sale.discount_amount || sale.discount)}
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            {getPaymentIcon(sale.payment_method)}
                            {getPaymentLabel(sale.payment_method)}
                          </div>
                          {(sale.discount_amount || sale.discount) > 0 && (
                            <div className="flex items-center gap-1.5 text-xs">
                              <Tag className="w-3 h-3 text-green-600" />
                              <span className="text-green-600 font-medium">
                                Rabais: -{formatAmount(sale.discount_amount || sale.discount)}
                              </span>
                            </div>
                          )}
                          {sale.has_debt && sale.debt_amount > 0 && (
                            <div className="flex items-center gap-1.5 text-xs">
                              <span className="text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">
                                Dette: {formatAmount(sale.debt_amount)}
                              </span>
                            </div>
                          )}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right font-medium text-teal-700" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {formatAmount(sale.total || 0)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleViewDetails(sale)}
                          data-testid={`view-sale-${sale.id}`}
                          title="Voir les détails"
                        >
                          <Eye className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => generateSalePDF(sale)}
                          data-testid={`pdf-sale-${sale.id}`}
                          className="text-teal-600 hover:text-teal-700 hover:bg-teal-50"
                          title="Télécharger le reçu PDF"
                        >
                          <FileText className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleReturnClick(sale)}
                          data-testid={`return-sale-${sale.id}`}
                          className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                          title="Retour d'articles"
                        >
                          <RotateCcw className="w-4 h-4" strokeWidth={1.5} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          
          {/* Indicateur de chargement infini et compteur */}
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 rounded-b-xl">
            <div className="flex items-center justify-between">
              <div className="text-sm text-slate-600">
                {sales.length} sur {totalSales} vente{totalSales > 1 ? 's' : ''} affichée{sales.length > 1 ? 's' : ''}
              </div>
              
              {/* Bouton charger plus ou indicateur */}
              <div className="flex items-center gap-2">
                {isFetchingNextPage && (
                  <div className="flex items-center gap-2 text-sm text-teal-600">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Chargement...</span>
                  </div>
                )}
                
                {hasNextPage && !isFetchingNextPage && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchNextPage()}
                    className="text-teal-700 border-teal-200 hover:bg-teal-50"
                  >
                    Charger plus
                  </Button>
                )}
                
                {/* Message fin de liste */}
                {!hasNextPage && sales.length > 0 && (
                  <div className="text-sm text-slate-400">
                    ✓ Fin de la liste
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Element invisible pour déclencher le chargement au scroll */}
          {hasNextPage && <div ref={loadMoreRef} className="h-10 w-full" />}
          
          {filteredSales.length === 0 && (
            <div className="text-center py-12">
              <ShoppingCart className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
              <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
                {searchQuery ? 'Aucune vente trouvée' : 'Aucune vente enregistrée'}
              </p>
            </div>
          )}
        </div>
        )}
      </div>

      {/* Dialog Détails de la vente */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>Détails de la vente</DialogTitle>
          </DialogHeader>
          {selectedSale && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Date</p>
                  <p className="font-medium">{new Date(selectedSale.created_at).toLocaleString('fr-FR')}</p>
                </div>
                <div>
                  <p className="text-slate-500">Client</p>
                  <p className="font-medium">{getCustomerName(selectedSale.customer_id)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Paiement</p>
                  {selectedSale.is_split_payment && selectedSale.split_payments ? (
                    <div className="space-y-1 mt-1">
                      {selectedSale.split_payments.map((sp, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm">
                          {getPaymentIcon(sp.method)}
                          <span className="font-medium">{getPaymentLabel(sp.method)}</span>
                          <span className="text-teal-600">{formatAmount(sp.amount)}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="font-medium flex items-center gap-2">
                      {getPaymentIcon(selectedSale.payment_method)}
                      {getPaymentLabel(selectedSale.payment_method)}
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-slate-500">Total</p>
                  <p className="font-medium text-teal-700">{formatAmount(selectedSale.total || 0)}</p>
                </div>
              </div>
              
              {/* Afficher les détails de dette si présente */}
              {selectedSale.has_debt && selectedSale.debt_amount > 0 && (
                <div className="p-3 bg-amber-50 rounded-lg border border-amber-200">
                  <div className="flex items-center gap-2 text-amber-800 mb-2">
                    <Wallet className="w-4 h-4" />
                    <span className="font-medium text-sm">Informations de dette</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <p className="text-amber-700">Payé</p>
                      <p className="font-medium text-amber-900">{formatAmount(selectedSale.amount_paid || 0)}</p>
                    </div>
                    <div>
                      <p className="text-amber-700">Restant dû</p>
                      <p className="font-medium text-amber-900">{formatAmount(selectedSale.debt_amount)}</p>
                    </div>
                  </div>
                </div>
              )}
              
              <div>
                <p className="text-sm text-slate-500 mb-2">Articles</p>
                <div className="space-y-2">
                  {selectedSale.items?.map((item, index) => {
                    // Adapter les noms de champs: unit_price -> price, product_name -> name
                    const itemName = item.product_name || item.name || 'Article inconnu';
                    const itemPrice = item.unit_price || item.price || 0;
                    return (
                      <div key={index} className="flex justify-between items-center p-3 bg-slate-50 rounded-lg">
                        <div>
                          <p className="font-medium">{itemName}</p>
                          <p className="text-sm text-slate-500">{formatAmount(itemPrice)} × {item.quantity}</p>
                        </div>
                        <p className="font-medium">{formatAmount(itemPrice * item.quantity)}</p>
                      </div>
                    );
                  })}
                </div>
              </div>
              
              {/* Afficher le résumé avec rabais si présent */}
              {(selectedSale.discount > 0 || selectedSale.discount_amount > 0) && (
                <div className="border-t pt-3 space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Sous-total</span>
                    <span className="font-medium">{formatAmount(selectedSale.subtotal || 0)}</span>
                  </div>
                  <div className="flex justify-between text-sm text-amber-700">
                    <span className="flex items-center gap-1">
                      <Percent className="w-3 h-3" />
                      Rabais {selectedSale.discount_type === 'percent' && selectedSale.discount_value ? `(${selectedSale.discount_value}%)` : ''}
                    </span>
                    <span className="font-medium">- {formatAmount(selectedSale.discount || selectedSale.discount_amount || 0)}</span>
                  </div>
                  <div className="flex justify-between text-base font-bold border-t pt-2">
                    <span className="text-slate-700">Total</span>
                    <span className="text-teal-700">{formatAmount(selectedSale.total || 0)}</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Retour d'articles */}
      <Dialog open={showReturnDialog} onOpenChange={setShowReturnDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Retour d&apos;articles
              {selectedSale && (
                <span className="ml-2 font-mono text-sm font-normal text-teal-600 bg-teal-50 px-2 py-1 rounded">
                  {selectedSale.sale_number || `VNT-${selectedSale.id?.substring(0, 8).toUpperCase()}`}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          {selectedSale && (
            <div className="space-y-4">
              <div className="text-sm text-slate-500 bg-amber-50 p-3 rounded-lg border border-amber-200">
                <p className="font-medium text-amber-800">⚠️ Note importante</p>
                <p className="text-amber-700 mt-1">
                  Le retour créera une nouvelle entrée dans l&apos;historique des opérations. 
                  La vente originale ne sera pas modifiée.
                </p>
              </div>
              
              <div>
                <p className="text-sm font-medium text-slate-700 mb-2">Sélectionnez les articles à retourner :</p>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {returnItems.map((item) => {
                    const maxReturn = item.sold_quantity - item.returned_quantity;
                    const isFullyReturned = maxReturn === 0;
                    return (
                      <div 
                        key={item.product_id} 
                        className={`flex items-center justify-between p-3 rounded-lg ${
                          isFullyReturned ? 'bg-slate-100 opacity-60' : 'bg-slate-50'
                        }`}
                      >
                        <div className="flex-1">
                          <p className="font-medium text-slate-900">{item.name}</p>
                          <p className="text-sm text-slate-500">
                            {formatAmount(item.price)} × {item.sold_quantity} vendu(s)
                            {item.returned_quantity > 0 && (
                              <span className="text-amber-600 ml-2">
                                ({item.returned_quantity} déjà retourné)
                              </span>
                            )}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {isFullyReturned ? (
                            <span className="text-xs text-slate-500 bg-slate-200 px-2 py-1 rounded">
                              Tout retourné
                            </span>
                          ) : (
                            <>
                              <Input
                                type="number"
                                min="0"
                                max={maxReturn}
                                value={item.return_quantity}
                                onChange={(e) => updateReturnQuantity(item.product_id, e.target.value)}
                                className="w-20 text-center"
                                data-testid={`return-qty-${item.product_id}`}
                              />
                              <span className="text-xs text-slate-400">/ {maxReturn}</span>
                            </>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div>
                <Label htmlFor="return-reason">
                  Motif du retour <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="return-reason"
                  placeholder="Ex: Produit endommagé, erreur de commande..."
                  value={returnReason}
                  onChange={(e) => setReturnReason(e.target.value)}
                  className={`mt-1 ${!returnReason.trim() && 'border-red-300 focus:border-red-500'}`}
                  required
                />
                {!returnReason.trim() && (
                  <p className="text-xs text-red-500 mt-1">Ce champ est obligatoire</p>
                )}
              </div>

              <div className="flex justify-between items-center p-4 bg-amber-50 rounded-lg border border-amber-200">
                <span className="text-lg font-semibold text-slate-900">Remboursement :</span>
                <span className="text-2xl font-bold text-amber-700">
                  {formatAmount(calculateRefundTotal())}
                </span>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setShowReturnDialog(false)}>
                  Annuler
                </Button>
                <Button 
                  onClick={handleReturnSubmit}
                  className="bg-amber-600 hover:bg-amber-700"
                  disabled={calculateRefundTotal() === 0 || !returnReason.trim()}
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Confirmer le retour
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Historique des opérations */}
      <Dialog open={showHistoryDialog} onOpenChange={setShowHistoryDialog}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Historique des opérations
              <span className="ml-2 text-sm font-normal text-slate-500">
                ({totalOperations} total)
              </span>
            </DialogTitle>
          </DialogHeader>
          
          {/* Filtres */}
          <div className="flex gap-2 mb-4">
            <Button 
              variant={historyFilter === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setHistoryFilter('all')}
              className={historyFilter === 'all' ? 'bg-slate-800' : ''}
            >
              Tout ({operationsHistory.length})
            </Button>
            <Button 
              variant={historyFilter === 'sales' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setHistoryFilter('sales')}
              className={historyFilter === 'sales' ? 'bg-teal-700' : ''}
            >
              <ShoppingCart className="w-4 h-4 mr-1" />
              Ventes ({operationsHistory.filter(o => o.type === 'sale').length})
            </Button>
            <Button 
              variant={historyFilter === 'returns' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setHistoryFilter('returns')}
              className={historyFilter === 'returns' ? 'bg-amber-600' : ''}
            >
              <RotateCcw className="w-4 h-4 mr-1" />
              Retours ({operationsHistory.filter(o => o.type === 'return').length})
            </Button>
          </div>
          
          <div 
            ref={historyScrollRef}
            className="overflow-y-auto flex-1 pr-2"
            onScroll={(e) => {
              const { scrollTop, scrollHeight, clientHeight } = e.target;
              // Charger plus quand on est à 100px du bas
              if (scrollHeight - scrollTop - clientHeight < 100 && historyHasNext && !historyFetchingNext) {
                fetchNextHistoryPage();
              }
            }}
          >
            <div className="space-y-3">
              {historyLoading && operationsHistory.length === 0 ? (
                <div className="text-center py-8">
                  <Loader2 className="w-8 h-8 animate-spin text-teal-600 mx-auto mb-2" />
                  <p className="text-slate-500">Chargement...</p>
                </div>
              ) : operationsHistory.filter(op => 
                historyFilter === 'all' || 
                (historyFilter === 'sales' && op.type === 'sale') ||
                (historyFilter === 'returns' && op.type === 'return')
              ).length === 0 ? (
                <p className="text-center text-slate-500 py-8">Aucune opération trouvée</p>
              ) : (
                <>
                  {operationsHistory
                    .filter(op => 
                      historyFilter === 'all' || 
                      (historyFilter === 'sales' && op.type === 'sale') ||
                      (historyFilter === 'returns' && op.type === 'return')
                    )
                    .map((op) => (
                    <div 
                      key={op.id} 
                      className={`p-4 rounded-lg border ${
                        op.type === 'sale' 
                          ? 'bg-teal-50 border-teal-200' 
                          : 'bg-amber-50 border-amber-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`p-2 rounded-full ${
                            op.type === 'sale' ? 'bg-teal-100' : 'bg-amber-100'
                          }`}>
                            {op.type === 'sale' ? (
                              <ShoppingCart className="w-5 h-5 text-teal-700" />
                            ) : (
                              <RotateCcw className="w-5 h-5 text-amber-700" />
                            )}
                          </div>
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className={`font-mono text-sm font-bold px-2 py-0.5 rounded ${
                                op.type === 'sale' ? 'bg-teal-100 text-teal-800' : 'bg-amber-100 text-amber-800'
                              }`}>
                                {op.operation_number}
                              </span>
                              {op.type === 'return' && op.sale_number && (
                                <span className="text-xs text-slate-500">
                                  → {op.sale_number}
                                </span>
                              )}
                              <span 
                                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${getAgentBadgeStyles(op.user_role)}`}
                                title={op.user_name || 'Inconnu'}
                              >
                                {op.employee_code || 'N/A'}
                              </span>
                            </div>
                            <p className="text-sm text-slate-500 mt-1">
                              {op.date ? new Date(op.date).toLocaleString('fr-FR') : 'Date inconnue'}
                            </p>
                            {op.type === 'return' && op.reason && (
                              <p className="text-sm text-amber-700 mt-1">
                                Motif : {op.reason}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="text-right flex flex-col items-end gap-2">
                          <p className={`text-lg font-bold ${
                            op.type === 'sale' ? 'text-teal-700' : 'text-amber-700'
                          }`}>
                            {op.type === 'sale' ? '+' : '-'}{formatAmount(op.amount)}
                          </p>
                          <p className="text-sm text-slate-500">
                            {op.items_count} article{op.items_count > 1 ? 's' : ''}
                          </p>
                          {op.type === 'return' && op.details && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedReturnDetail(op.details);
                                setShowReturnDetailDialog(true);
                              }}
                              className="text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                            >
                              <Eye className="w-4 h-4 mr-1" />
                              Détails
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                  
                  {/* Indicateur de chargement pour infinite scroll */}
                  {historyFetchingNext && (
                    <div className="text-center py-4">
                      <Loader2 className="w-6 h-6 animate-spin text-teal-600 mx-auto" />
                    </div>
                  )}
                  
                  {/* Message fin de liste */}
                  {!historyHasNext && operationsHistory.length > 0 && (
                    <p className="text-center text-sm text-slate-400 py-4">
                      Fin de l&apos;historique
                    </p>
                  )}
                </>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog Détails du retour */}
      <Dialog open={showReturnDetailDialog} onOpenChange={setShowReturnDetailDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Détails du retour
              {selectedReturnDetail && (
                <span className="ml-2 font-mono text-sm font-normal text-amber-600 bg-amber-50 px-2 py-1 rounded">
                  {selectedReturnDetail.return_number || `RET-${selectedReturnDetail.id?.substring(0, 8).toUpperCase()}`}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>
          {selectedReturnDetail && (
            <div className="space-y-4">
              {/* Infos du retour */}
              <div className="p-4 bg-slate-50 rounded-lg space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Vente associée:</span>
                  <span className="font-mono font-semibold text-teal-700">
                    {selectedReturnDetail.sale_number || `VNT-${selectedReturnDetail.sale_id?.substring(0, 8).toUpperCase()}`}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Date du retour:</span>
                  <span className="font-medium">
                    {new Date(selectedReturnDetail.created_at).toLocaleString('fr-FR')}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-500">Agent:</span>
                  <span className="font-mono font-medium">
                    {selectedReturnDetail.employee_code || 'N/A'}
                  </span>
                </div>
                {selectedReturnDetail.reason && (
                  <div className="pt-2 border-t border-slate-200">
                    <span className="text-sm text-slate-500 block">Motif:</span>
                    <p className="text-sm text-amber-700 font-medium mt-1">
                      {selectedReturnDetail.reason}
                    </p>
                  </div>
                )}
              </div>

              {/* Articles retournés */}
              <div>
                <h4 className="font-semibold text-slate-900 mb-2">Articles retournés</h4>
                <div className="space-y-2">
                  {selectedReturnDetail.items?.map((item, index) => {
                    const itemName = item.product_name || item.name || 'Article inconnu';
                    const itemPrice = item.unit_price || item.price || 0;
                    const itemQuantity = item.quantity || 1;
                    const itemRefund = item.refund_amount || item.refund || (itemQuantity * itemPrice);
                    
                    return (
                      <div key={index} className="flex justify-between items-center p-3 bg-amber-50 rounded-lg border border-amber-100">
                        <div>
                          <p className="font-medium text-slate-900">{itemName}</p>
                          <p className="text-sm text-slate-500">
                            {itemQuantity} × {formatAmount(itemPrice)}
                          </p>
                        </div>
                        <span className="font-semibold text-amber-700">
                          {formatAmount(itemRefund)}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Total remboursé */}
              <div className="flex justify-between items-center p-4 bg-amber-100 rounded-lg border border-amber-200">
                <span className="text-lg font-semibold text-slate-900">Total remboursé:</span>
                <span className="text-2xl font-bold text-amber-700">
                  {formatAmount(selectedReturnDetail.total_refund)}
                </span>
              </div>

              <DialogFooter>
                <Button variant="outline" onClick={() => setShowReturnDetailDialog(false)}>
                  Fermer
                </Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Ventes en attente */}
      <Dialog open={showPendingSalesDialog} onOpenChange={setShowPendingSalesDialog}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              <div className="flex items-center gap-2">
                <Pause className="w-5 h-5 text-amber-500" />
                Ventes en attente
                {pendingSalesCount?.count > 0 && (
                  <span className="bg-amber-500 text-white text-sm px-2 py-0.5 rounded-full">
                    {pendingSalesCount.count}
                  </span>
                )}
              </div>
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {pendingSalesLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
              </div>
            ) : pendingSales.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Pause className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p>Aucune vente en attente</p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingSales.map((pending) => (
                  <div 
                    key={pending.id}
                    className="border border-slate-200 rounded-xl p-4 hover:border-amber-300 hover:bg-amber-50/50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                            {pending.reference}
                          </span>
                          {pending.customer_name && (
                            <span className="text-sm text-slate-600">
                              • {pending.customer_name}
                            </span>
                          )}
                        </div>
                        
                        {/* Liste des produits */}
                        <div className="text-sm text-slate-600 mb-2">
                          {pending.items.slice(0, 3).map((item, idx) => (
                            <span key={idx}>
                              {item.product_name} x{item.quantity}
                              {idx < Math.min(pending.items.length, 3) - 1 && ', '}
                            </span>
                          ))}
                          {pending.items.length > 3 && (
                            <span className="text-slate-400"> +{pending.items.length - 3} autres</span>
                          )}
                        </div>
                        
                        {/* Info créateur et expiration */}
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <span>
                            Par {pending.created_by_name}
                          </span>
                          <span className={`flex items-center gap-1 ${
                            pending.time_remaining_minutes < 60 ? 'text-red-500' : 
                            pending.time_remaining_minutes < 180 ? 'text-amber-500' : 'text-slate-500'
                          }`}>
                            <Clock className="w-3 h-3" />
                            {formatTimeRemaining(pending.time_remaining_minutes)}
                          </span>
                        </div>
                      </div>
                      
                      {/* Montant et actions */}
                      <div className="text-right ml-4">
                        <p className="font-bold text-lg text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
                          {formatAmount(pending.total)}
                        </p>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCancelPendingSale(pending)}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                            disabled={cancelPendingSale.isPending}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleResumePendingSale(pending)}
                            className="bg-amber-500 hover:bg-amber-600 text-white"
                            disabled={cancelPendingSale.isPending}
                          >
                            <Play className="w-4 h-4 mr-1" />
                            Reprendre
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            <div className="text-xs text-slate-400 text-center pt-2 border-t">
              Les ventes en attente expirent automatiquement après 24 heures
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Barcode Scanner */}
      {showBarcodeScanner && (
        <BarcodeScanner
          onScan={handleBarcodeScan}
          onClose={() => setShowBarcodeScanner(false)}
        />
      )}
    </Layout>
  );
};

export default Sales;
