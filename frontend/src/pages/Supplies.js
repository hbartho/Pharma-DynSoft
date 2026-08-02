import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Package, 
  Truck, 
  CheckCircle2, 
  Clock, 
  FileText,
  Calendar,
  User,
  ShoppingCart,
  AlertTriangle,
  Eye,
  X,
  RefreshCw,
  PlusCircle,
  ScanLine,
  Loader2,
  Timer
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import BarcodeScanner from '../components/BarcodeScanner';
import { useQueryClient } from '@tanstack/react-query';
import { useSupplies, useCreateSupply, useUpdateSupply, useDeleteSupply, useValidateSupply } from '../hooks/useSupplies';
import api from '../services/api';
import { useSuppliesInfinite } from '../hooks/useInfiniteScroll';
import { useSuppliers, useCreateSupplier } from '../hooks/useSuppliers';
import { useProducts, useCreateProduct } from '../hooks/useProducts';
import { useCategories } from '../hooks/useCategories';
import { useUnits } from '../hooks/useUnits';
import { useSettingsQuery } from '../hooks/useSettings';
import { SkeletonSuppliesPage } from '../components/ui/skeleton-shimmer';
import { useCurrentShift, useCanOperate } from '../hooks/useShifts';
import { useShiftEligibility } from '../hooks/useShiftSchedules';

const Supplies = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const loadMoreRef = useRef(null);
  
  // Vérifier si l'utilisateur peut effectuer des opérations (admin exempté)
  const { data: currentShift } = useCurrentShift();
  const { canOperate, reason: shiftBlockReason } = useCanOperate(user, currentShift);
  
  // Vérifier l'éligibilité de planification (pour restreindre l'accès hors horaires)
  const { data: shiftEligibility } = useShiftEligibility();
  const isAdmin = user?.role === 'admin';
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  // Rôle de l'utilisateur
  const userRole = user?.role;
  const userEmployeeCode = user?.employee_code;
  const isAdminOrPharmacien = userRole === 'admin' || userRole === 'pharmacien';
  
  // États pour filtres et recherche
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);
  
  // Fonction pour vérifier si l'utilisateur peut éditer/supprimer un approvisionnement
  const canEditSupply = (supply) => {
    // Si l'appro est validé, personne ne peut le modifier
    if (supply.is_validated) return false;
    // Admin et Pharmacien peuvent tout modifier
    if (isAdminOrPharmacien) return true;
    // Caissier peut modifier uniquement ses propres appros (comparer avec employee_code)
    return supply.created_by === userEmployeeCode;
  };
  
  // React Query hooks avec infinite scroll
  const { 
    data: suppliesData,
    isLoading: suppliesLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch: refetchSupplies 
  } = useSuppliesInfinite({
    limit: 20,
    search: debouncedSearch,
    status: filterStatus === 'all' ? '' : filterStatus
  });
  
  const supplies = suppliesData?.pages?.flatMap(page => page.items) || [];
  const totalSupplies = suppliesData?.pages?.[0]?.total || 0;
  
  // Garder useSupplies pour les formulaires si nécessaire
  const { data: allSupplies = [] } = useSupplies();
  
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

  const { data: allSuppliers = [], isLoading: suppliersLoading, refetch: refetchSuppliers } = useSuppliers();
  const { data: allProducts = [], isLoading: productsLoading, refetch: refetchProducts } = useProducts();
  const { data: categories = [], isLoading: categoriesLoading } = useCategories();
  const { data: units = [], isLoading: unitsLoading } = useUnits();
  const { data: appSettings = { currency: 'GNF' } } = useSettingsQuery();
  
  // Filter active suppliers and products
  const suppliers = allSuppliers.filter(s => s.is_active !== false);
  const products = allProducts.filter(p => p.is_active !== false);
  
  // Mutations
  const createSupply = useCreateSupply();
  const updateSupply = useUpdateSupply();
  const deleteSupply = useDeleteSupply();
  const validateSupply = useValidateSupply();
  const createSupplier = useCreateSupplier();
  const createProduct = useCreateProduct();
  
  // Local state
  const [showDialog, setShowDialog] = useState(false);
  const [showViewDialog, setShowViewDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showValidateDialog, setShowValidateDialog] = useState(false);
  const [showAddSupplierDialog, setShowAddSupplierDialog] = useState(false);
  const [showAddProductDialog, setShowAddProductDialog] = useState(false);
  const [showBarcodeScanner, setShowBarcodeScanner] = useState(false);
  const [editingSupply, setEditingSupply] = useState(null);
  const [viewingSupply, setViewingSupply] = useState(null);
  const [supplyToDelete, setSupplyToDelete] = useState(null);
  const [supplyToValidate, setSupplyToValidate] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [loadingSupplyDetails, setLoadingSupplyDetails] = useState(false);
  
  // Derived loading state
  const loading = suppliesLoading || suppliersLoading || productsLoading;
  
  // Fonction pour obtenir la date locale au format YYYY-MM-DD
  const getLocalDateString = (date = new Date()) => {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Form state
  const [formData, setFormData] = useState({
    supply_date: getLocalDateString(),
    supplier_id: '',
    purchase_order_ref: '',
    delivery_note_number: '',
    invoice_number: '',
    notes: '',
    items: []
  });
  
  // Item form state
  const [itemForm, setItemForm] = useState({
    product_id: '',
    quantity: '',
    unit_price: '',
    prix_public_modifie: '', // Prix public modifié (optionnel, doit être >= prix_public_base)
    date_peremption: '',
    lot_number: '',
    shelf_location: '',
    tva_rate: '0'
  });
  const [editingItemId, setEditingItemId] = useState(null); // ID de l'item en cours d'édition
  const [productSearch, setProductSearch] = useState('');
  const [selectedProductInfo, setSelectedProductInfo] = useState(null);
  const [prixPublicWarning, setPrixPublicWarning] = useState(false); // Warning si prix modifié < prix base // Pour afficher stock actuel, coefficient, prix calculé

  // Quick add supplier form
  const [supplierForm, setSupplierForm] = useState({
    name: '',
    contact: '',
    phone: '',
    email: '',
    address: ''
  });

  // Quick add product form
  const [productForm, setProductForm] = useState({
    name: '',
    internal_reference: '',
    barcode: '',
    description: '',
    category_id: '',
    unit_id: ''
  });

  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  // Rafraîchir le formulaire
  const refreshForm = useCallback(() => {
    setRefreshKey(prev => prev + 1);
    queryClient.invalidateQueries({ queryKey: ['products'] });
    queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    toast.success('Liste mise à jour');
  }, [queryClient]);

  const resetForm = () => {
    setEditingSupply(null);
    setEditingItemId(null);
    setFormData({
      supply_date: getLocalDateString(),
      supplier_id: '',
      purchase_order_ref: '',
      delivery_note_number: '',
      invoice_number: '',
      is_credit_note: false,
      notes: '',
      items: []
    });
    setItemForm({ product_id: '', quantity: '', unit_price: '', prix_public_modifie: '', date_peremption: '', lot_number: '', shelf_location: '', tva_rate: '0' });
    setProductSearch('');
    setSelectedProductInfo(null);
  };

  const handleAddItem = () => {
    if (!itemForm.product_id || !itemForm.quantity || !itemForm.unit_price) {
      toast.error('Veuillez remplir Produit, Quantité et Prix d\'achat');
      return;
    }
    
    // Date de péremption obligatoire
    if (!itemForm.date_peremption) {
      toast.error('La date de péremption est obligatoire');
      return;
    }
    
    // Vérifier que la date de péremption est supérieure à aujourd'hui
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const expirationDate = new Date(itemForm.date_peremption);
    if (expirationDate <= today) {
      toast.error('La date de péremption doit être supérieure à la date actuelle');
      return;
    }
    
    const product = products.find(p => p.id === itemForm.product_id);
    if (!product) return;
    
    const category = categories.find(c => c.id === product?.category_id);
    const coefficient = category?.markup_coefficient || 1.0;
    const purchasePrice = parseFloat(itemForm.unit_price);  // Prix Cession
    const tvaRate = parseFloat(itemForm.tva_rate) || 0;
    const quantity = parseInt(itemForm.quantity);
    
    // Prix Public Base = Prix Cession × Coefficient (calculé automatiquement)
    const prixPublicBase = Math.round(purchasePrice * coefficient);
    
    // Prix Public Modifié (saisi par l'utilisateur, optionnel)
    // Note: Peut être inférieur au prix de base (cas de rabais ou liquidation)
    const prixPublicModifie = itemForm.prix_public_modifie 
      ? parseFloat(itemForm.prix_public_modifie) 
      : null;
    
    // Le prix de vente final = Prix Public Modifié (si fourni) OU Prix Public Base
    const sellingPrice = prixPublicModifie !== null ? prixPublicModifie : prixPublicBase;
    
    // Mettre à jour le prix de base du produit en arrière-plan (silencieusement)
    // Le prix de vente (price) du produit = Prix Public Base calculé
    api.put(`/products/${product.id}`, {
      price: prixPublicBase,  // Prix public base = Prix Cession × Coefficient
      purchase_price: purchasePrice  // Mettre à jour aussi le prix d'achat
    }).then(() => {
      // Mettre à jour selectedProductInfo pour refléter le nouveau prix
      setSelectedProductInfo(prev => prev ? {
        ...prev,
        selling_price: prixPublicBase
      } : null);
      // Rafraîchir la liste des produits
      refetchProducts();
    }).catch((err) => {
      // Silencieux - ne pas bloquer l'ajout de l'item si la mise à jour du produit échoue
      console.warn('Mise à jour du prix produit échouée:', err);
    });
    
    // Prix TTC = Prix de vente × (1 + TVA/100)
    const prixTTC = tvaRate > 0 
      ? Math.round(sellingPrice * (1 + tvaRate / 100)) 
      : sellingPrice;
    
    // Total = Prix Cession × Quantité × (1 + TVA/100)
    // C'est le montant que l'on paye au fournisseur (coût d'achat TTC)
    const totalPrice = tvaRate > 0
      ? Math.round(purchasePrice * quantity * (1 + tvaRate / 100))
      : purchasePrice * quantity;
    
    // Si on édite un item existant (via editingItemId)
    if (editingItemId) {
      const existingIndex = formData.items.findIndex(item => item.id === editingItemId);
      
      if (existingIndex >= 0) {
        const updatedItems = [...formData.items];
        updatedItems[existingIndex] = {
          ...updatedItems[existingIndex],
          product_id: itemForm.product_id,
          product_name: product.name,
          quantity: quantity,
          unit_price: purchasePrice,
          total_price: totalPrice,
          prix_public_base: prixPublicBase,
          prix_public_modifie: prixPublicModifie,
          prix_ttc: prixTTC,
          date_peremption: itemForm.date_peremption || null,
          lot_number: itemForm.lot_number || null,
          shelf_location: itemForm.shelf_location || null,
          tva_rate: tvaRate,
          current_stock: product?.stock || 0,
          category_name: category?.name || 'Non catégorisé',
          markup_coefficient: coefficient,
          selling_price: sellingPrice  // Prix final utilisé (modifié ou base)
        };
        setFormData({ ...formData, items: updatedItems });
        toast.success(`Produit "${product.name}" mis à jour`);
      }
    } else {
      // Ajouter un nouvel item
      const newItem = {
        id: crypto.randomUUID(),
        product_id: itemForm.product_id,
        product_name: product.name,
        quantity: quantity,
        unit_price: purchasePrice,
        total_price: totalPrice,
        prix_public_base: prixPublicBase,
        prix_public_modifie: prixPublicModifie,
        prix_ttc: prixTTC,
        date_peremption: itemForm.date_peremption || null,
        lot_number: itemForm.lot_number || null,
        shelf_location: itemForm.shelf_location || null,
        tva_rate: tvaRate,
        // Champs calculés pour affichage
        current_stock: product?.stock || 0,
        category_name: category?.name || 'Non catégorisé',
        markup_coefficient: coefficient,
        selling_price: sellingPrice
      };
      setFormData({ ...formData, items: [...formData.items, newItem] });
      toast.success(`Produit "${product.name}" ajouté`);
    }
    
    // Réinitialiser le formulaire
    setEditingItemId(null);
    setItemForm({ product_id: '', quantity: '', unit_price: '', prix_public_modifie: '', date_peremption: '', lot_number: '', shelf_location: '', tva_rate: '0' });
    setProductSearch('');
    setSelectedProductInfo(null);
    setPrixPublicWarning(false);
    refreshForm();
  };

  const handleRemoveItem = (itemId) => {
    const item = formData.items.find(i => i.id === itemId);
    setFormData({
      ...formData,
      items: formData.items.filter(item => item.id !== itemId)
    });
    toast.success(`Produit "${item?.product_name}" retiré`);
    refreshForm();
  };

  const handleEditItem = (item) => {
    setEditingItemId(item.id); // Marquer l'item comme étant en édition
    setItemForm({
      product_id: item.product_id,
      quantity: item.quantity.toString(),
      unit_price: item.unit_price.toString(),
      prix_public_modifie: item.prix_public_modifie ? item.prix_public_modifie.toString() : '',
      date_peremption: item.date_peremption ? item.date_peremption.split('T')[0] : '',
      lot_number: item.lot_number || '',
      shelf_location: item.shelf_location || '',
      tva_rate: (item.tva_rate || 0).toString()
    });
    setProductSearch(item.product_name);
    
    // Récupérer le coefficient depuis le produit/catégorie si non présent dans l'item
    let coefficient = item.markup_coefficient || 1.0;
    if (!item.markup_coefficient) {
      const product = products.find(p => p.id === item.product_id);
      if (product) {
        const category = categories.find(c => c.id === product.category_id);
        coefficient = category?.markup_coefficient || 1.0;
      }
    }
    
    setSelectedProductInfo({
      name: item.product_name,
      current_stock: item.current_stock || 0,
      category_name: item.category_name || 'Non catégorisé',
      markup_coefficient: coefficient,
      selling_price: item.selling_price || 0
    });
  };

  const handleSelectProduct = (productId) => {
    const product = products.find(p => p.id === productId);
    if (product) {
      // Récupérer les infos de la catégorie pour le coefficient
      const category = categories.find(c => c.id === product.category_id);
      const coefficient = category?.markup_coefficient || 1.0;
      const purchasePrice = product.purchase_price || 0;
      const sellingPrice = Math.round(purchasePrice * coefficient);
      
      // Ne pas pré-remplir les prix - laisser l'utilisateur saisir
      setItemForm({
        ...itemForm,
        product_id: productId,
        unit_price: '',  // Laisser vide pour saisie utilisateur
        prix_public_modifie: ''  // Laisser vide pour saisie utilisateur
      });
      setSelectedProductInfo({
        name: product.name,
        current_stock: product.stock || 0,
        category_name: category?.name || 'Non catégorisé',
        markup_coefficient: coefficient,
        selling_price: sellingPrice,
        last_purchase_price: purchasePrice  // Garder en info pour référence
      });
      setProductSearch('');
    }
  };

  // Handler pour le changement du prix de cession - recalcule automatiquement le prix public modifié
  const handleUnitPriceChange = (newUnitPrice) => {
    const priceValue = newUnitPrice === '' ? '' : newUnitPrice;
    
    // Si on a un produit sélectionné et un prix de cession valide, recalculer le prix public modifié
    if (selectedProductInfo && priceValue !== '' && !isNaN(parseFloat(priceValue))) {
      const coefficient = selectedProductInfo.markup_coefficient || 1.0;
      const newPrixPublic = Math.round(parseFloat(priceValue) * coefficient);
      
      setItemForm({
        ...itemForm,
        unit_price: priceValue,
        prix_public_modifie: newPrixPublic.toString()
      });
    } else {
      setItemForm({
        ...itemForm,
        unit_price: priceValue
      });
    }
  };
  
  // Calcul du prix public BASE (pour affichage info) = Prix Cession × Coefficient
  const calculatedPrixPublicBase = useMemo(() => {
    if (!itemForm.unit_price || !selectedProductInfo) return 0;
    const coefficient = selectedProductInfo.markup_coefficient || 1.0;
    return Math.round(parseFloat(itemForm.unit_price) * coefficient);
  }, [itemForm.unit_price, selectedProductInfo]);

  // Handle barcode scan
  const handleBarcodeScan = (barcode) => {
    const product = products.find(p => p.barcode === barcode);
    if (product) {
      handleSelectProduct(product.id);
      toast.success(`Produit trouvé: ${product.name}`);
    } else {
      toast.error(`Aucun produit trouvé avec le code-barres: ${barcode}`);
    }
    setShowBarcodeScanner(false);
  };

  const calculateTotal = () => {
    return formData.items.reduce((sum, item) => sum + (item.total_price || 0), 0);
  };

  // Quick add supplier
  const handleAddSupplier = async (e) => {
    e.preventDefault();
    createSupplier.mutate(supplierForm, {
      onSuccess: (newSupplier) => {
        setShowAddSupplierDialog(false);
        setSupplierForm({ name: '', contact: '', phone: '', email: '', address: '' });
        // Sélectionner automatiquement le nouveau fournisseur
        setFormData({ ...formData, supplier_id: newSupplier.id });
      },
    });
  };

  // Quick add product
  const handleAddProduct = async (e) => {
    e.preventDefault();
    const productData = {
      name: productForm.name,
      internal_reference: productForm.internal_reference || null,
      barcode: productForm.barcode || null,
      description: productForm.description || null,
      category_id: productForm.category_id || null,
      unit_id: productForm.unit_id || null
    };
    createProduct.mutate(productData, {
      onSuccess: (newProduct) => {
        setShowAddProductDialog(false);
        setProductForm({ name: '', internal_reference: '', barcode: '', description: '', category_id: '', unit_id: '' });
        // Pré-sélectionner le nouveau produit
        handleSelectProduct(newProduct.id);
      },
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validation des champs obligatoires
    if (!formData.supplier_id) {
      toast.error('Veuillez sélectionner un fournisseur');
      return;
    }
    
    if (!formData.delivery_note_number) {
      toast.error('Veuillez saisir le N° Bon de livraison');
      return;
    }
    
    if (!formData.invoice_number) {
      toast.error('Veuillez saisir le N° Facture');
      return;
    }
    
    if (formData.items.length === 0) {
      toast.error('Veuillez ajouter au moins un produit');
      return;
    }
    
    // Préserver la date locale en ajoutant l'heure locale actuelle
    const supplyDateWithTime = new Date(formData.supply_date + 'T12:00:00');
    
    const submitData = {
      supply_date: supplyDateWithTime.toISOString(),
      supplier_id: formData.supplier_id,
      purchase_order_ref: formData.purchase_order_ref || null,
      delivery_note_number: formData.delivery_note_number,
      invoice_number: formData.invoice_number,
      is_credit_note: formData.is_credit_note,
      notes: formData.notes || null,
      items: formData.items.map(item => ({
        product_id: item.product_id,
        quantity: item.quantity,
        unit_price: item.unit_price,
        date_peremption: item.date_peremption || null,
        lot_number: item.lot_number || null,
        shelf_location: item.shelf_location || null,
        tva_rate: item.tva_rate || 0,
        prix_public_modifie: item.prix_public_modifie || null
      }))
    };
    
    if (editingSupply) {
      updateSupply.mutate(
        { supplyId: editingSupply.id, data: submitData },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      createSupply.mutate(submitData, {
        onSuccess: () => {
          toast.success('Approvisionnement créé (en attente de validation)');
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const handleEdit = async (supply) => {
    if (supply.is_validated) {
      toast.error('Impossible de modifier un approvisionnement validé');
      return;
    }
    
    // Afficher un état de chargement
    setLoadingSupplyDetails(true);
    
    try {
      // Récupérer les détails complets de l'approvisionnement (avec les items)
      const response = await api.get(`/supplies/${supply.id}`);
      const fullSupply = response.data;
      
      // Recalculer les totaux selon: Total = Prix Cession × Qté × (1 + TVA/100)
      const itemsWithTotals = (fullSupply.items || []).map(item => {
        const quantity = item.quantity || 0;
        const unitPrice = item.unit_price || 0;  // Prix Cession
        const coefficient = item.markup_coefficient || 1;
        const tvaRate = item.tva_rate || 0;
        
        // Prix Public de base = Prix Cession × Coef (TOUJOURS calculé)
        const prixPublicBase = Math.round(unitPrice * coefficient);
        
        // Prix TTC = Prix Cession × Coef × (1 + TVA/100)
        const prixTTC = tvaRate > 0 ? Math.round(prixPublicBase * (1 + tvaRate / 100)) : prixPublicBase;
        
        // TOTAL = Prix Cession × Qté × (1 + TVA/100) - C'est le coût d'achat TTC
        const totalPrice = tvaRate > 0 
          ? Math.round(unitPrice * quantity * (1 + tvaRate / 100))
          : unitPrice * quantity;
        
        // Récupérer le prix public modifié (peut être stocké dans prix_public_modifie ou selling_price)
        let prixPublicModifie = item.prix_public_modifie;
        if (!prixPublicModifie && item.selling_price && item.selling_price !== prixPublicBase) {
          prixPublicModifie = item.selling_price;
        }
        
        return {
          ...item,
          id: item.id || crypto.randomUUID(), // Assurer un ID pour chaque item
          prix_public_base: prixPublicBase,
          prix_public_modifie: prixPublicModifie,
          prix_ttc: prixTTC,
          total_price: totalPrice
        };
      });
      
      setEditingSupply(fullSupply);
      setFormData({
        supply_date: fullSupply.supply_date ? getLocalDateString(fullSupply.supply_date) : getLocalDateString(),
        supplier_id: fullSupply.supplier_id || '',
        purchase_order_ref: fullSupply.purchase_order_ref || '',
        delivery_note_number: fullSupply.delivery_note_number || '',
        invoice_number: fullSupply.invoice_number || '',
        is_credit_note: fullSupply.is_credit_note || false,
        notes: fullSupply.notes || '',
        items: itemsWithTotals
      });
      setShowDialog(true);
    } catch (error) {
      console.error('Erreur lors de la récupération des détails:', error);
      toast.error('Erreur lors de la récupération des articles');
    } finally {
      setLoadingSupplyDetails(false);
    }
  };

  const handleView = async (supply) => {
    // Afficher un état de chargement
    setLoadingSupplyDetails(true);
    
    try {
      // Récupérer les détails complets de l'approvisionnement (avec les items)
      const response = await api.get(`/supplies/${supply.id}`);
      const fullSupply = response.data;
      setViewingSupply(fullSupply);
      setShowViewDialog(true);
    } catch (error) {
      console.error('Erreur lors de la récupération des détails:', error);
      toast.error('Erreur lors de la récupération des détails');
      // Fallback: afficher avec les données disponibles
      setViewingSupply(supply);
      setShowViewDialog(true);
    } finally {
      setLoadingSupplyDetails(false);
    }
  };

  const handleDelete = (supply) => {
    if (supply.is_validated) {
      toast.error('Impossible de supprimer un approvisionnement validé');
      return;
    }
    setSupplyToDelete(supply);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!supplyToDelete) return;
    
    deleteSupply.mutate(supplyToDelete.id, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        setSupplyToDelete(null);
      },
      onError: () => {
        setShowDeleteDialog(false);
        setSupplyToDelete(null);
      },
    });
  };

  const handleValidate = async (supply) => {
    if (!isAdmin) {
      toast.error('Seul un administrateur peut valider un approvisionnement');
      return;
    }
    
    // Charger les détails complets de l'approvisionnement pour afficher les items
    setLoadingSupplyDetails(true);
    try {
      const response = await api.get(`/supplies/${supply.id}`);
      const fullSupply = response.data;
      setSupplyToValidate(fullSupply);
      setShowValidateDialog(true);
    } catch (error) {
      console.error('Erreur lors du chargement des détails:', error);
      toast.error('Erreur lors du chargement des détails de l\'approvisionnement');
    } finally {
      setLoadingSupplyDetails(false);
    }
  };

  const handleValidateConfirm = async () => {
    if (!supplyToValidate) return;
    
    validateSupply.mutate(supplyToValidate.id, {
      onSuccess: () => {
        setShowValidateDialog(false);
        setSupplyToValidate(null);
      },
      onError: () => {
        setShowValidateDialog(false);
        setSupplyToValidate(null);
      },
    });
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    
    // Utiliser le timezone configuré dans les paramètres
    const timezone = appSettings?.timezone || 'Africa/Conakry';
    
    // Si la date est au format YYYY-MM-DD (sans heure), c'est une date locale
    if (typeof dateString === 'string' && dateString.length === 10 && dateString.includes('-')) {
      // Format YYYY-MM-DD - parser comme date locale sans conversion timezone
      const [year, month, day] = dateString.split('-').map(Number);
      const date = new Date(year, month - 1, day);
      return date.toLocaleDateString('fr-FR', { 
        day: '2-digit', 
        month: 'short', 
        year: 'numeric' 
      });
    }
    
    // Pour les dates avec heure/timezone (ISO), utiliser le timezone configuré
    const date = new Date(dateString);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      timeZone: timezone
    });
  };

  // Les données sont déjà filtrées côté serveur
  const sortedSupplies = [...supplies].sort((a, b) => {
    // Non validés en premier, puis par date
    if (a.is_validated !== b.is_validated) {
      return a.is_validated ? 1 : -1;
    }
    return new Date(b.created_at || 0) - new Date(a.created_at || 0);
  });

  const pendingCount = supplies.filter(s => s.is_validated === false).length;
  const validatedCount = supplies.filter(s => s.is_validated === true).length;

  const filteredProducts = products.filter(p => 
    productSearch && (
      p.name?.toLowerCase().includes(productSearch.toLowerCase()) ||
      p.internal_reference?.toLowerCase().includes(productSearch.toLowerCase()) ||
      p.barcode?.toLowerCase().includes(productSearch.toLowerCase())
    )
  );

  // Loading state avec skeleton shimmer
  if (suppliesLoading && supplies.length === 0) {
    return (
      <Layout>
        <SkeletonSuppliesPage />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="supplies-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Approvisionnements
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des entrées de stock • {supplies.length} appro{supplies.length > 1 ? 's' : ''}
            </p>
          </div>
          <Dialog open={showDialog} onOpenChange={(open) => { 
            setShowDialog(open); 
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button 
                data-testid="add-supply-button" 
                size="sm"
                className="bg-teal-700 hover:bg-teal-800 rounded-full w-full sm:w-auto"
                disabled={!canOperate}
                title={!canOperate ? shiftBlockReason : ""}
              >
                <Plus className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
                <span className="hidden sm:inline">Nouvel approvisionnement</span>
                <span className="sm:hidden">Nouvelle appro</span>
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingSupply ? 'Modifier l\'approvisionnement' : 'Nouvel approvisionnement'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-6">
                {/* Info générale */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="supply_date">Date d'approvisionnement *</Label>
                    <Input
                      id="supply_date"
                      type="date"
                      value={formData.supply_date}
                      onChange={(e) => setFormData({ ...formData, supply_date: e.target.value })}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="supplier" className="flex items-center justify-between">
                      <span>Fournisseur <span className="text-red-500">*</span></span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowAddSupplierDialog(true)}
                        className="h-6 px-2 text-xs text-teal-600 hover:text-teal-700"
                      >
                        <PlusCircle className="w-3 h-3 mr-1" />
                        Nouveau
                      </Button>
                    </Label>
                    <Select 
                      value={formData.supplier_id || 'none'} 
                      onValueChange={(value) => setFormData({ ...formData, supplier_id: value === 'none' ? '' : value })}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue placeholder="Sélectionner un fournisseur" />
                      </SelectTrigger>
                      <SelectContent>
                        {suppliers.map((supplier) => (
                          <SelectItem key={supplier.id} value={supplier.id}>
                            {supplier.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="purchase_order_ref">Réf. Bon de commande</Label>
                    <Input
                      id="purchase_order_ref"
                      value={formData.purchase_order_ref}
                      onChange={(e) => setFormData({ ...formData, purchase_order_ref: e.target.value })}
                      placeholder="BC-001"
                      className="mt-1"
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="delivery_note_number">N° Bon de livraison <span className="text-red-500">*</span></Label>
                    <Input
                      id="delivery_note_number"
                      value={formData.delivery_note_number}
                      onChange={(e) => setFormData({ ...formData, delivery_note_number: e.target.value })}
                      placeholder="BL-001"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="invoice_number">N° Facture <span className="text-red-500">*</span></Label>
                    <Input
                      id="invoice_number"
                      value={formData.invoice_number}
                      onChange={(e) => setFormData({ ...formData, invoice_number: e.target.value })}
                      placeholder="FACT-001"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="total_ttc">Total TTC Facture</Label>
                    <Input
                      id="total_ttc"
                      value={formatAmount(calculateTotal())}
                      readOnly
                      disabled
                      className="mt-1 bg-slate-100 font-bold text-red-700"
                    />
                  </div>
                </div>
                
                <div>
                  <Label htmlFor="notes">Notes</Label>
                  <Input
                    id="notes"
                    value={formData.notes}
                    onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                    placeholder="Notes ou observations..."
                    className="mt-1"
                  />
                </div>

                {/* Section Produits */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium text-slate-900 flex items-center gap-2">
                      <Package className="w-5 h-5 text-teal-600" />
                      Produits à approvisionner
                    </h3>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => setShowAddProductDialog(true)}
                      className="text-teal-600 hover:text-teal-700"
                    >
                      <PlusCircle className="w-4 h-4 mr-1" />
                      Nouveau produit
                    </Button>
                  </div>
                  
                  {/* Formulaire d'ajout de produit */}
                  <div className="p-4 bg-slate-50 rounded-lg mb-4" key={refreshKey}>
                    {/* Recherche produit */}
                    <div className="relative mb-4">
                      <Label className="text-sm">Rechercher un produit</Label>
                      <div className="relative mt-1 flex gap-2">
                        <div className="relative flex-1">
                          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                          <Input
                            placeholder="Nom, référence ou code-barres..."
                            value={productSearch}
                            onChange={(e) => setProductSearch(e.target.value)}
                            className="pl-9"
                          />
                        </div>
                        <Button
                          type="button"
                          variant="outline"
                          onClick={() => setShowBarcodeScanner(true)}
                          className="shrink-0 border-teal-200 text-teal-700 hover:bg-teal-50 hover:border-teal-300"
                          title="Scanner un code-barres"
                        >
                          <ScanLine className="w-4 h-4" />
                        </Button>
                      </div>
                      {productSearch && filteredProducts.length > 0 && (
                        <div className="absolute z-10 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                          {filteredProducts.slice(0, 8).map(product => (
                            <button
                              key={product.id}
                              type="button"
                              onClick={() => handleSelectProduct(product.id)}
                              className="w-full text-left px-3 py-2 hover:bg-slate-50 flex justify-between items-center"
                            >
                              <div>
                                <p className="font-medium text-sm">{product.name}</p>
                                <p className="text-xs text-slate-500">
                                  {product.internal_reference && `Réf: ${product.internal_reference}`}
                                  {product.internal_reference && product.barcode && ' • '}
                                  {product.barcode && `Code: ${product.barcode}`}
                                </p>
                              </div>
                              <span className="text-xs text-slate-400">Stock: {product.stock}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {itemForm.product_id && (
                        <p className="text-xs text-teal-600 mt-1">
                          ✓ {products.find(p => p.id === itemForm.product_id)?.name}
                        </p>
                      )}
                    </div>
                    
                    {/* Champs lot: Périme le, N° Lot, Rayon, TVA */}
                    <div className="grid grid-cols-4 gap-3 mb-4">
                      <div>
                        <Label className="text-sm">Périme le <span className="text-red-500">*</span></Label>
                        <Input
                          type="date"
                          value={itemForm.date_peremption}
                          onChange={(e) => setItemForm({ ...itemForm, date_peremption: e.target.value })}
                          min={new Date(Date.now() + 86400000).toISOString().split('T')[0]}
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">N° Lot <span className="text-red-500">*</span></Label>
                        <Input
                          type="text"
                          value={itemForm.lot_number}
                          onChange={(e) => setItemForm({ ...itemForm, lot_number: e.target.value })}
                          placeholder="LOT-XXXX"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Rayon</Label>
                        <Input
                          type="text"
                          value={itemForm.shelf_location}
                          onChange={(e) => setItemForm({ ...itemForm, shelf_location: e.target.value })}
                          placeholder="A1, B2..."
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">TVA (%)</Label>
                        <Input
                          type="number"
                          step="0.1"
                          min="0"
                          max="100"
                          value={itemForm.tva_rate}
                          onChange={(e) => setItemForm({ ...itemForm, tva_rate: e.target.value })}
                          placeholder="0"
                          className="mt-1"
                        />
                      </div>
                    </div>
                    
                    {/* Quantité et Prix */}
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <Label className="text-sm">Quantité <span className="text-red-500">*</span></Label>
                        <Input
                          type="number"
                          min="1"
                          value={itemForm.quantity}
                          onChange={(e) => setItemForm({ ...itemForm, quantity: e.target.value })}
                          placeholder="0"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label className="text-sm">Prix de cession <span className="text-red-500">*</span></Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={itemForm.unit_price}
                          onChange={(e) => handleUnitPriceChange(e.target.value)}
                          placeholder="0.00"
                          className="mt-1"
                        />
                        {selectedProductInfo && selectedProductInfo.last_purchase_price > 0 && (
                          <p className="text-xs text-slate-500 mt-1">
                            Dernier prix: {formatAmount(selectedProductInfo.last_purchase_price)}
                          </p>
                        )}
                      </div>
                      <div>
                        <Label className="text-sm">
                          Prix public modifié
                          <span className="text-slate-400 text-xs ml-1">(optionnel)</span>
                        </Label>
                        <Input
                          type="number"
                          step="0.01"
                          min="0"
                          value={itemForm.prix_public_modifie}
                          onChange={(e) => setItemForm({ ...itemForm, prix_public_modifie: e.target.value })}
                          placeholder="0.00"
                          className="mt-1"
                        />
                      </div>
                    </div>
                    
                    {/* Informations de référence */}
                    {selectedProductInfo && (
                      <div className="mt-3 p-3 bg-gradient-to-r from-teal-50 to-emerald-50 rounded-lg border border-teal-100">
                        <div className="flex flex-wrap items-center justify-between gap-y-2 text-sm">
                          <div className="whitespace-nowrap">
                            <span className="text-slate-500">Stock:</span>
                            <span className={`ml-1 font-medium ${selectedProductInfo.current_stock <= 10 ? 'text-red-600' : 'text-slate-900'}`}>
                              {selectedProductInfo.current_stock}
                            </span>
                          </div>
                          <div className="whitespace-nowrap">
                            <span className="text-slate-500">Catégorie:</span>
                            <span className="ml-1 font-medium text-slate-900">{selectedProductInfo.category_name}</span>
                          </div>
                          <div className="whitespace-nowrap">
                            <span className="text-slate-500">Coef.:</span>
                            <span className="ml-1 font-medium text-teal-700">×{selectedProductInfo.markup_coefficient}</span>
                          </div>
                          <div className="whitespace-nowrap">
                            <span className="text-slate-500">P. Public Modifié:</span>
                            <span className="ml-1 font-bold text-emerald-700">
                              {formatAmount(
                                itemForm.prix_public_modifie 
                                  ? parseFloat(itemForm.prix_public_modifie) 
                                  : Math.round((parseFloat(itemForm.unit_price) || selectedProductInfo.last_purchase_price || 0) * (selectedProductInfo.markup_coefficient || 1))
                              )}
                            </span>
                          </div>
                          {/* Marge - toujours visible */}
                          <div className="whitespace-nowrap bg-white px-2 py-0.5 rounded border border-green-200">
                            <span className="text-slate-500">Marge:</span>
                            <span className="ml-1 font-bold">
                              {(() => {
                                const prixCession = parseFloat(itemForm.unit_price) || 0;
                                const prixPublicBase = Math.round(prixCession * (selectedProductInfo.markup_coefficient || 1));
                                const prixVente = itemForm.prix_public_modifie 
                                  ? parseFloat(itemForm.prix_public_modifie) 
                                  : prixPublicBase;
                                const margePct = prixCession > 0 ? Math.round((prixVente - prixCession) / prixCession * 100) : 0;
                                const isPositive = margePct >= 0;
                                return (
                                  <span className={isPositive ? 'text-green-600' : 'text-red-600'}>
                                    {isPositive ? '+' : ''}{margePct}%
                                  </span>
                                );
                              })()}
                            </span>
                          </div>
                          {/* Aperçu du Total calculé en temps réel - toujours visible */}
                          <div className="whitespace-nowrap bg-white px-2 py-0.5 rounded border border-teal-200">
                            <span className="text-slate-500">Total:</span>
                            <span className="ml-1 font-bold text-teal-700">
                              {(() => {
                                const qty = parseInt(itemForm.quantity) || 0;
                                const unitPrice = parseFloat(itemForm.unit_price) || 0;
                                const tva = parseFloat(itemForm.tva_rate) || 0;
                                // Total = Prix Cession × Quantité × (1 + TVA/100)
                                const total = tva > 0 
                                  ? Math.round(unitPrice * qty * (1 + tva / 100))
                                  : unitPrice * qty;
                                return formatAmount(total);
                              })()}
                            </span>
                          </div>
                        </div>
                        
                        {/* Warning: Prix Public Modifié < Prix de base */}
                        {itemForm.prix_public_modifie && itemForm.unit_price && (() => {
                          const prixCession = parseFloat(itemForm.unit_price) || 0;
                          const prixPublicBase = Math.round(prixCession * (selectedProductInfo.markup_coefficient || 1));
                          const prixModifie = parseFloat(itemForm.prix_public_modifie);
                          return prixModifie < prixPublicBase;
                        })() && (
                          <div className="mt-2 p-2 bg-amber-50 border border-amber-300 rounded-lg flex items-center gap-2 text-amber-800">
                            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
                            <span className="text-xs">
                              <span className="font-medium">Attention :</span> Prix modifié ({formatAmount(parseFloat(itemForm.prix_public_modifie))}) &lt; Prix base ({formatAmount(Math.round(parseFloat(itemForm.unit_price) * (selectedProductInfo.markup_coefficient || 1)))}) — Marge réduite (rabais/liquidation)
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                    
                    <div className="mt-3 flex justify-end gap-2">
                      {editingItemId && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setEditingItemId(null);
                            setItemForm({ product_id: '', quantity: '', unit_price: '', prix_public_modifie: '', date_peremption: '', lot_number: '', shelf_location: '', tva_rate: '0' });
                            setProductSearch('');
                            setSelectedProductInfo(null);
                          }}
                        >
                          Annuler
                        </Button>
                      )}
                      <Button
                        type="button"
                        onClick={handleAddItem}
                        size="sm"
                        disabled={!itemForm.product_id || !itemForm.quantity || !itemForm.unit_price || !itemForm.lot_number || !itemForm.date_peremption}
                        className={editingItemId 
                          ? "bg-blue-600 hover:bg-blue-700 text-white" 
                          : "bg-teal-700 hover:bg-teal-800 text-white disabled:bg-gray-300 disabled:text-gray-500"
                        }
                      >
                        {editingItemId ? (
                          <>
                            <Edit className="w-4 h-4 mr-1" />
                            Modifier le produit
                          </>
                        ) : (
                          <>
                            <Plus className="w-4 h-4 mr-1" />
                            Ajouter le produit
                          </>
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Liste des produits */}
                  {formData.items.length === 0 ? (
                    <div className="text-center py-8 border-2 border-dashed border-slate-200 rounded-lg">
                      <Package className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                      <p className="text-sm text-slate-500">Aucun produit ajouté</p>
                      <p className="text-xs text-slate-400">Recherchez et ajoutez des produits ci-dessus</p>
                    </div>
                  ) : (
                    <div className="border border-slate-200 rounded-lg overflow-hidden">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-50">
                          <tr>
                            <th className="text-left px-3 py-2 font-medium text-slate-600">Produit</th>
                            <th className="text-center px-2 py-2 font-medium text-slate-600">Stock</th>
                            <th className="text-right px-2 py-2 font-medium text-slate-600">Qté</th>
                            <th className="text-right px-2 py-2 font-medium text-slate-600">P. Cession</th>
                            <th className="text-center px-2 py-2 font-medium text-slate-600">Coef.</th>
                            <th className="text-right px-2 py-2 font-medium text-slate-600">P. Public</th>
                            <th className="text-center px-2 py-2 font-medium text-slate-600">Péremption</th>
                            <th className="text-center px-2 py-2 font-medium text-slate-600">N° Lot</th>
                            <th className="text-center px-2 py-2 font-medium text-slate-600">Rayon</th>
                            <th className="text-right px-2 py-2 font-medium text-slate-600">TVA</th>
                            <th className="text-right px-2 py-2 font-medium text-slate-600">P. TTC</th>
                            <th className="text-right px-3 py-2 font-medium text-slate-600">Total</th>
                            <th className="px-2 py-2 w-16"></th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                          {formData.items.map((item) => (
                            <tr key={item.id} className="hover:bg-slate-50">
                              <td className="px-3 py-2 font-medium text-slate-900">
                                <div>{item.product_name}</div>
                                <div className="text-xs text-slate-500">{item.category_name || ''}</div>
                              </td>
                              <td className="px-2 py-2 text-center">
                                <span className={`text-xs px-1.5 py-0.5 rounded ${item.current_stock <= 10 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'}`}>
                                  {item.current_stock || 0}
                                </span>
                              </td>
                              <td className="px-2 py-2 text-right font-medium text-teal-700">{item.quantity}</td>
                              <td className="px-2 py-2 text-right">{formatAmount(item.unit_price)}</td>
                              <td className="px-2 py-2 text-center text-teal-600">×{item.markup_coefficient || 1}</td>
                              <td className="px-2 py-2 text-right font-medium text-emerald-700">
                                {formatAmount(item.prix_public_base || item.selling_price || 0)}
                                {item.selling_price && item.prix_public_base && item.selling_price !== item.prix_public_base && (
                                  <div className="text-xs text-orange-600">Modifié: {formatAmount(item.selling_price)}</div>
                                )}
                              </td>
                              <td className="px-2 py-2 text-center text-xs">
                                {item.date_peremption ? new Date(item.date_peremption).toLocaleDateString('fr-FR') : '-'}
                              </td>
                              <td className="px-2 py-2 text-center text-xs">{item.lot_number || '-'}</td>
                              <td className="px-2 py-2 text-center text-xs">{item.shelf_location || '-'}</td>
                              <td className="px-2 py-2 text-right text-xs">{item.tva_rate || 0}%</td>
                              <td className="px-2 py-2 text-right font-medium text-orange-600">{formatAmount(item.prix_ttc || item.selling_price || 0)}</td>
                              <td className="px-3 py-2 text-right font-medium">{formatAmount(item.total_price)}</td>
                              <td className="px-2 py-2">
                                <div className="flex gap-1 justify-end">
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleEditItem(item)}
                                    className="text-blue-600 hover:text-blue-700 hover:bg-blue-50 h-7 w-7 p-0"
                                    title="Modifier"
                                  >
                                    <Edit className="w-3.5 h-3.5" />
                                  </Button>
                                  <Button
                                    type="button"
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleRemoveItem(item.id)}
                                    className="text-red-600 hover:text-red-700 hover:bg-red-50 h-7 w-7 p-0"
                                    title="Supprimer"
                                  >
                                    <X className="w-3.5 h-3.5" />
                                  </Button>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="bg-teal-50">
                          <tr>
                            <td colSpan="11" className="px-4 py-3 font-medium text-slate-700 text-right">
                              Total approvisionnement ({formData.items.length} produit{formData.items.length > 1 ? 's' : ''})
                            </td>
                            <td className="px-4 py-3 text-right font-bold text-teal-700 text-lg">{formatAmount(calculateTotal())}</td>
                            <td></td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-4 border-t">
                  <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                    Annuler
                  </Button>
                  <Button type="submit" className="bg-teal-700 hover:bg-teal-800" disabled={formData.items.length === 0}>
                    {editingSupply ? 'Mettre à jour' : 'Enregistrer (en attente)'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-100 rounded-lg">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{pendingCount}</p>
                <p className="text-sm text-slate-500">En attente</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-100 rounded-lg">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{validatedCount}</p>
                <p className="text-sm text-slate-500">Validés</p>
              </div>
            </div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-100">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-teal-100 rounded-lg">
                <ShoppingCart className="w-5 h-5 text-teal-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{supplies.length}</p>
                <p className="text-sm text-slate-500">Total</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              placeholder="Rechercher par ID, référence, bon de livraison, facture ou fournisseur..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus} disabled={!isWithinScheduledHours}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filtrer par statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              <SelectItem value="pending">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-600" />
                  En attente
                </div>
              </SelectItem>
              <SelectItem value="validated">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  Validés
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
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
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux approvisionnements en dehors de vos horaires planifiés.'}
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
        {/* Supplies List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-700 mx-auto"></div>
            <p className="text-slate-500 mt-4">Chargement...</p>
          </div>
        ) : sortedSupplies.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">Aucun approvisionnement trouvé</p>
          </div>
        ) : (
          <div className="space-y-4">
            {sortedSupplies.map((supply) => (
              <div
                key={supply.id}
                className={`bg-white rounded-xl border p-4 transition-all ${
                  supply.is_validated 
                    ? 'border-emerald-200' 
                    : 'border-amber-200 bg-amber-50/30'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${
                        supply.is_validated 
                          ? 'bg-emerald-100 text-emerald-700' 
                          : 'bg-amber-100 text-amber-700'
                      }`}>
                        {supply.is_validated ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            Validé
                          </>
                        ) : (
                          <>
                            <Clock className="w-3.5 h-3.5" />
                            En attente
                          </>
                        )}
                      </span>
                      {supply.is_credit_note && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                          Avoir
                        </span>
                      )}
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          Date
                        </p>
                        <p className="font-medium text-slate-900">{formatDate(supply.supply_date)}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Truck className="w-3.5 h-3.5" />
                          Fournisseur
                        </p>
                        <p className="font-medium text-slate-900">{supply.supplier_name || 'Non spécifié'}</p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5" />
                          Références
                        </p>
                        <p className="font-medium text-slate-900 text-xs">
                          {supply.purchase_order_ref && <span className="block">BC: {supply.purchase_order_ref}</span>}
                          {supply.delivery_note_number && <span className="block">BL: {supply.delivery_note_number}</span>}
                          {supply.invoice_number && <span className="block">Fact: {supply.invoice_number}</span>}
                          {!supply.purchase_order_ref && !supply.delivery_note_number && !supply.invoice_number && '-'}
                        </p>
                      </div>
                      <div>
                        <p className="text-slate-500 flex items-center gap-1">
                          <Package className="w-3.5 h-3.5" />
                          Produits / Montant
                        </p>
                        <p className="font-medium text-slate-900">
                          {supply.items_count ?? supply.items?.length ?? 0} article{(supply.items_count ?? supply.items?.length ?? 0) > 1 ? 's' : ''}
                        </p>
                        <p className="font-bold text-teal-700">{formatAmount(supply.total_amount)}</p>
                      </div>
                    </div>
                    
                    <div className="mt-2 text-xs text-slate-500">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        Saisi par <span className="font-mono font-medium text-slate-700">{supply.created_by_name || supply.created_by || 'N/A'}</span> le {formatDate(supply.created_at)}
                        {supply.updated_by_name && (
                          <span className="ml-2 text-blue-600">
                            • Modifié par <span className="font-mono font-medium">{supply.updated_by_name}</span>
                          </span>
                        )}
                        {supply.is_validated && supply.validated_at && (
                          <span className="ml-2 text-emerald-600">
                            • Validé par <span className="font-mono font-medium">{supply.validated_by_name || 'N/A'}</span> le {formatDate(supply.validated_at)}
                          </span>
                        )}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleView(supply)}
                      title="Voir détails"
                      disabled={loadingSupplyDetails}
                    >
                      {loadingSupplyDetails ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </Button>
                    {!supply.is_validated && (
                      <>
                        {isAdmin && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleValidate(supply)}
                            className="text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                            title="Valider (Admin uniquement)"
                          >
                            <CheckCircle2 className="w-4 h-4" />
                          </Button>
                        )}
                        {canEditSupply(supply) && (
                          <>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleEdit(supply)}
                              title="Modifier"
                              disabled={loadingSupplyDetails}
                            >
                              {loadingSupplyDetails ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <Edit className="w-4 h-4" />
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDelete(supply)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              title="Supprimer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Infinite Scroll Loader */}
            <div className="flex flex-col items-center gap-4 py-6">
              <p className="text-sm text-slate-600">
                {sortedSupplies.length} sur {totalSupplies} approvisionnements affichés
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
                  Charger plus d'approvisionnements
                </Button>
              )}
              {!hasNextPage && sortedSupplies.length > 0 && (
                <p className="text-sm text-slate-400">✓ Tous les approvisionnements ont été chargés</p>
              )}
            </div>
          </div>
        )}
        </>
        )}
      </div>

      {/* View Dialog */}
      <Dialog open={showViewDialog} onOpenChange={setShowViewDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-teal-600" />
              Détails de l'approvisionnement
            </DialogTitle>
          </DialogHeader>
          {viewingSupply && (
            <div className="space-y-4">
              <div className="flex items-center gap-2 mb-4">
                <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-sm font-medium ${
                  viewingSupply.is_validated 
                    ? 'bg-emerald-100 text-emerald-700' 
                    : 'bg-amber-100 text-amber-700'
                }`}>
                  {viewingSupply.is_validated ? (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      Validé
                    </>
                  ) : (
                    <>
                      <Clock className="w-4 h-4" />
                      En attente de validation
                    </>
                  )}
                </span>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-slate-500">Date d'approvisionnement</p>
                  <p className="font-medium">{formatDate(viewingSupply.supply_date)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Fournisseur</p>
                  <p className="font-medium">{viewingSupply.supplier_name || 'Non spécifié'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Réf. Bon de commande</p>
                  <p className="font-medium">{viewingSupply.purchase_order_ref || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">N° Bon de livraison</p>
                  <p className="font-medium">{viewingSupply.delivery_note_number || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">N° Facture</p>
                  <p className="font-medium">{viewingSupply.invoice_number || '-'}</p>
                </div>
                <div>
                  <p className="text-slate-500">Saisi par</p>
                  <p className="font-medium font-mono">{viewingSupply.created_by_name || viewingSupply.created_by || 'N/A'}</p>
                </div>
                {viewingSupply.updated_by_name && (
                  <div>
                    <p className="text-slate-500">Modifié par</p>
                    <p className="font-medium font-mono text-blue-600">{viewingSupply.updated_by_name}</p>
                  </div>
                )}
                {viewingSupply.is_validated && (
                  <div>
                    <p className="text-slate-500">Validé par</p>
                    <p className="font-medium font-mono text-emerald-600">{viewingSupply.validated_by_name || 'N/A'}</p>
                  </div>
                )}
              </div>
              
              {viewingSupply.notes && (
                <div>
                  <p className="text-slate-500 text-sm">Notes</p>
                  <p className="font-medium">{viewingSupply.notes}</p>
                </div>
              )}
              
              <div className="border-t pt-4">
                <h4 className="font-medium text-slate-900 mb-3">Produits ({viewingSupply.items?.length || 0})</h4>
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  <div className="max-h-[220px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 sticky top-0">
                        <tr>
                          <th className="text-left px-4 py-2 font-medium text-slate-600">Produit</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Qté</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Prix unit.</th>
                          <th className="text-right px-4 py-2 font-medium text-slate-600">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {viewingSupply.items?.map((item, index) => {
                          const itemTotal = (item.quantity || 0) * (item.unit_price || 0);
                          return (
                            <tr key={index} className="hover:bg-slate-50">
                              <td className="px-4 py-2 font-medium">{item.product_name}</td>
                              <td className="px-4 py-2 text-right">{item.quantity}</td>
                              <td className="px-4 py-2 text-right">{formatAmount(item.unit_price)}</td>
                              <td className="px-4 py-2 text-right font-medium">{formatAmount(itemTotal)}</td>
                          </tr>
                        );
                      })}
                      </tbody>
                    </table>
                  </div>
                  <div className="bg-teal-50 border-t border-slate-200">
                    <div className="flex justify-between px-4 py-3">
                      <span className="font-medium">Total</span>
                      <span className="font-bold text-teal-700">
                        {formatAmount(
                          viewingSupply.total_amount || 
                          viewingSupply.items?.reduce((sum, item) => sum + ((item.quantity || 0) * (item.unit_price || 0)), 0) || 
                          0
                        )}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Quick Add Supplier Dialog */}
      <Dialog open={showAddSupplierDialog} onOpenChange={setShowAddSupplierDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-teal-600" />
              Nouveau fournisseur
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddSupplier} className="space-y-4">
            <div>
              <Label htmlFor="supplier-name">Nom *</Label>
              <Input
                id="supplier-name"
                value={supplierForm.name}
                onChange={(e) => setSupplierForm({ ...supplierForm, name: e.target.value })}
                required
                placeholder="Nom du fournisseur"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="supplier-contact">Contact</Label>
              <Input
                id="supplier-contact"
                value={supplierForm.contact}
                onChange={(e) => setSupplierForm({ ...supplierForm, contact: e.target.value })}
                placeholder="Personne de contact"
                className="mt-1"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="supplier-phone">Téléphone</Label>
                <Input
                  id="supplier-phone"
                  value={supplierForm.phone}
                  onChange={(e) => setSupplierForm({ ...supplierForm, phone: e.target.value })}
                  placeholder="+224 xxx"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="supplier-email">Email</Label>
                <Input
                  id="supplier-email"
                  type="email"
                  value={supplierForm.email}
                  onChange={(e) => setSupplierForm({ ...supplierForm, email: e.target.value })}
                  placeholder="email@exemple.com"
                  className="mt-1"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="supplier-address">Adresse</Label>
              <Input
                id="supplier-address"
                value={supplierForm.address}
                onChange={(e) => setSupplierForm({ ...supplierForm, address: e.target.value })}
                placeholder="Adresse complète"
                className="mt-1"
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowAddSupplierDialog(false)}>
                Annuler
              </Button>
              <Button type="submit" className="bg-teal-700 hover:bg-teal-800">
                Ajouter
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Quick Add Product Dialog */}
      <Dialog open={showAddProductDialog} onOpenChange={setShowAddProductDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-teal-600" />
              Nouveau produit
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddProduct} className="space-y-4">
            {/* Nom et Référence */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="product-name">Nom du produit *</Label>
                <Input
                  id="product-name"
                  value={productForm.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    // Générer référence automatique
                    const cleanName = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z]/g, '');
                    let ref = '';
                    if (cleanName.length >= 2) {
                      const firstPart = cleanName.substring(0, Math.min(4, cleanName.length)).toUpperCase();
                      const lastLetter = cleanName.charAt(cleanName.length - 1).toUpperCase();
                      const counter = (products.length + 1).toString().padStart(3, '0');
                      ref = `${firstPart}${counter}${lastLetter}`;
                    }
                    setProductForm({ ...productForm, name: name, internal_reference: ref });
                  }}
                  required
                  placeholder="Nom du produit"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="product-ref" className="flex items-center gap-1">
                  <span className="text-slate-400">#</span> Référence interne (auto)
                </Label>
                <Input
                  id="product-ref"
                  value={productForm.internal_reference}
                  readOnly
                  disabled
                  placeholder="Ex: MED-001"
                  className="mt-1 bg-slate-100 text-slate-500 cursor-not-allowed"
                />
              </div>
            </div>
            
            {/* Code-barres */}
            <div>
              <Label htmlFor="product-barcode">Code-barres</Label>
              <Input
                id="product-barcode"
                value={productForm.barcode}
                onChange={(e) => setProductForm({ ...productForm, barcode: e.target.value })}
                placeholder="123456789"
                className="mt-1"
              />
            </div>
            
            {/* Description */}
            <div>
              <Label htmlFor="product-description">Description</Label>
              <Input
                id="product-description"
                value={productForm.description || ''}
                onChange={(e) => setProductForm({ ...productForm, description: e.target.value })}
                placeholder="Description du produit"
                className="mt-1"
              />
            </div>
            
            {/* Catégorie et Unité */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="product-category">Catégorie</Label>
                <Select 
                  value={productForm.category_id || 'none'} 
                  onValueChange={(value) => setProductForm({ ...productForm, category_id: value === 'none' ? '' : value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Sans catégorie" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sans catégorie</SelectItem>
                    {categories.map((cat) => (
                      <SelectItem key={cat.id} value={cat.id}>
                        {cat.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="product-unit">Unité</Label>
                <Select 
                  value={productForm.unit_id || 'none'} 
                  onValueChange={(value) => setProductForm({ ...productForm, unit_id: value === 'none' ? '' : value })}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Sans unité" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Sans unité</SelectItem>
                    {units.map((unit) => (
                      <SelectItem key={unit.id} value={unit.id}>
                        {unit.name} ({unit.abbreviation})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            {/* Info box */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <div className="flex gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium text-amber-800">Prix et Stock</p>
                  <p className="text-xs text-amber-700 mt-1">
                    Les prix de cession, prix public, stock et dates de péremption sont gérés automatiquement lors des <strong>approvisionnements</strong>.
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="outline" onClick={() => setShowAddProductDialog(false)}>
                Annuler
              </Button>
              <Button type="submit" className="bg-teal-700 hover:bg-teal-800">
                Ajouter
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer cet approvisionnement ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowDeleteDialog(false); setSupplyToDelete(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Validate Confirmation - Dialog avec récapitulatif détaillé */}
      <AlertDialog open={showValidateDialog} onOpenChange={setShowValidateDialog}>
        <AlertDialogContent className="bg-white max-w-4xl max-h-[90vh] overflow-y-auto">
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="w-6 h-6 text-emerald-600" />
              Confirmer la validation de l'approvisionnement
            </AlertDialogTitle>
          </AlertDialogHeader>
          
          {supplyToValidate && (
            <div className="space-y-4">
              {/* Informations générales */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <span className="text-xs text-slate-500">N° Facture</span>
                  <p className="font-semibold text-slate-900">{supplyToValidate.invoice_number || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">N° Bon de livraison</span>
                  <p className="font-semibold text-slate-900">{supplyToValidate.delivery_note_number || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">Fournisseur</span>
                  <p className="font-semibold text-slate-900">{supplyToValidate.supplier_name || 'Non spécifié'}</p>
                </div>
                <div>
                  <span className="text-xs text-slate-500">Date</span>
                  <p className="font-semibold text-slate-900">{formatDate(supplyToValidate.supply_date)}</p>
                </div>
              </div>
              
              {/* Tableau des produits */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-slate-100 px-4 py-2 border-b">
                  <h4 className="font-semibold text-slate-700">
                    Produits à approvisionner ({supplyToValidate.items?.length || 0})
                  </h4>
                </div>
                <div className="max-h-64 overflow-y-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 sticky top-0">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-slate-600">Produit</th>
                        <th className="text-right px-2 py-2 font-medium text-slate-600">Qté</th>
                        <th className="text-right px-2 py-2 font-medium text-slate-600">P. Cession</th>
                        <th className="text-right px-2 py-2 font-medium text-slate-600">P. Public</th>
                        <th className="text-center px-2 py-2 font-medium text-slate-600">Péremption</th>
                        <th className="text-center px-2 py-2 font-medium text-slate-600">N° Lot</th>
                        <th className="text-right px-2 py-2 font-medium text-slate-600">TVA</th>
                        <th className="text-right px-3 py-2 font-medium text-slate-600">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {supplyToValidate.items?.map((item, idx) => {
                        const prixPublicBase = item.prix_public_base || item.selling_price || (item.unit_price * (item.markup_coefficient || 1));
                        const prixTTC = item.prix_ttc || (item.tva_rate > 0 ? Math.round(prixPublicBase * (1 + item.tva_rate / 100)) : prixPublicBase);
                        const total = prixTTC * item.quantity;
                        return (
                          <tr key={idx} className="hover:bg-slate-50">
                            <td className="px-3 py-2">
                              <div className="font-medium text-slate-900">{item.product_name}</div>
                              {item.category_name && <div className="text-xs text-slate-500">{item.category_name}</div>}
                            </td>
                            <td className="px-2 py-2 text-right font-semibold text-teal-700">{item.quantity}</td>
                            <td className="px-2 py-2 text-right">{formatAmount(item.unit_price)}</td>
                            <td className="px-2 py-2 text-right font-medium text-emerald-700">{formatAmount(prixPublicBase)}</td>
                            <td className="px-2 py-2 text-center text-xs">
                              {item.date_peremption ? new Date(item.date_peremption).toLocaleDateString('fr-FR') : '-'}
                            </td>
                            <td className="px-2 py-2 text-center text-xs font-mono">{item.lot_number || '-'}</td>
                            <td className="px-2 py-2 text-right text-xs">{item.tva_rate || 0}%</td>
                            <td className="px-3 py-2 text-right font-semibold">{formatAmount(total)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                    <tfoot className="bg-slate-100 font-semibold">
                      <tr>
                        <td colSpan="7" className="px-3 py-2 text-right">Total approvisionnement :</td>
                        <td className="px-3 py-2 text-right text-teal-700 text-lg">
                          {formatAmount(supplyToValidate.items?.reduce((acc, item) => {
                            const prixPublicBase = item.prix_public_base || item.selling_price || (item.unit_price * (item.markup_coefficient || 1));
                            const prixTTC = item.prix_ttc || (item.tva_rate > 0 ? Math.round(prixPublicBase * (1 + item.tva_rate / 100)) : prixPublicBase);
                            return acc + (prixTTC * item.quantity);
                          }, 0) || 0)}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
              
              {/* Avertissement */}
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-amber-800">Cette action est irréversible</p>
                    <ul className="list-disc list-inside mt-1 text-sm text-amber-700">
                      <li>Les stocks des {supplyToValidate.items?.length || 0} produit(s) seront mis à jour</li>
                      <li>Les lots de stock seront créés avec les N° Lot et dates de péremption</li>
                      <li>L'approvisionnement ne pourra plus être modifié</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <AlertDialogFooter className="flex gap-2 mt-4">
            <AlertDialogCancel onClick={() => { setShowValidateDialog(false); setSupplyToValidate(null); }}>
              Annuler
            </AlertDialogCancel>
            <Button 
              variant="outline" 
              onClick={() => { 
                setShowValidateDialog(false); 
                if (supplyToValidate) handleEdit(supplyToValidate);
              }}
              className="text-blue-600 border-blue-300 hover:bg-blue-50"
            >
              <Edit className="w-4 h-4 mr-2" />
              Modifier d'abord
            </Button>
            <AlertDialogAction onClick={handleValidateConfirm} className="bg-emerald-600 hover:bg-emerald-700">
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Valider l'approvisionnement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

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

export default Supplies;
