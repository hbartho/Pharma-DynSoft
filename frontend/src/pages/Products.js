import React, { useEffect, useState, useRef } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Plus, Search, Edit, Trash2, Package, Tag, Settings, Power, PowerOff, AlertTriangle, Calculator, TrendingUp, Box, Hash, Calendar, Clock, Loader2, CloudOff, Timer } from 'lucide-react';
import { getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { 
  useProducts,
  useProductsInfinite,
  useToggleProductStatus 
} from '../hooks/useProducts';
import { 
  useCategories, 
  useCreateCategory, 
  useUpdateCategory, 
  useDeleteCategory 
} from '../hooks/useCategories';
import { 
  useUnits, 
  useCreateUnit, 
  useUpdateUnit, 
  useDeleteUnit 
} from '../hooks/useUnits';
import { useSettingsQuery } from '../hooks/useSettings';
import { useOfflineMutation } from '../services/offlineMutations';
import { SkeletonProductsPage } from '../components/ui/skeleton-shimmer';
import { useShiftEligibility } from '../hooks/useShiftSchedules';

const Products = () => {
  const { user } = useAuth();
  const { isOnline } = useOffline();
  const queryClient = useQueryClient();
  
  // Vérifier l'éligibilité de planification (pour restreindre l'accès hors horaires)
  const { data: shiftEligibility } = useShiftEligibility();
  const isAdmin = user?.role === 'admin';
  const isWithinScheduledHours = isAdmin || shiftEligibility?.is_eligible;
  
  // Local state pour filtres
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  
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
    data: productsData,
    isLoading: productsLoading, 
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
    refetch: refetchProducts 
  } = useProductsInfinite({
    limit: 20,
    search: debouncedSearch,
    categoryId: filterCategory,
    status: filterStatus
  });
  
  // Aplatir les pages en une seule liste
  const products = productsData?.pages?.flatMap(page => page.items) || [];
  const totalProducts = productsData?.pages?.[0]?.total || 0;
  
  // Garder aussi la liste complète pour les formulaires
  const { data: allProducts = [] } = useProducts();
  
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
  
  const { data: categories = [], isLoading: categoriesLoading, refetch: refetchCategories } = useCategories();
  const { data: units = [], isLoading: unitsLoading, refetch: refetchUnits } = useUnits();
  const { data: appSettings = { currency: 'GNF', expiration_alert_days: 30 } } = useSettingsQuery();
  
  // Offline-first mutations for products
  const createProduct = useOfflineMutation('products', 'create');
  const updateProduct = useOfflineMutation('products', 'update');
  const deleteProduct = useOfflineMutation('products', 'delete');
  const toggleProductStatus = useToggleProductStatus();
  
  // Standard mutations for categories and units (less critical for offline)
  const createCategory = useCreateCategory();
  const updateCategory = useUpdateCategory();
  const deleteCategory = useDeleteCategory();
  const createUnit = useCreateUnit();
  const updateUnit = useUpdateUnit();
  const deleteUnit = useDeleteUnit();

  // Local state
  const [showDialog, setShowDialog] = useState(false);
  const [showCategoryDialog, setShowCategoryDialog] = useState(false);
  const [showUnitDialog, setShowUnitDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingUnit, setEditingUnit] = useState(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showDeleteCategoryDialog, setShowDeleteCategoryDialog] = useState(false);
  const [showDeleteUnitDialog, setShowDeleteUnitDialog] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [unitToDelete, setUnitToDelete] = useState(null);
  const [productSearchInForm, setProductSearchInForm] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    internal_reference: '',
    barcode: '',
    description: '',
    category_id: '',
    unit_id: '',
  });
  const [minStockFormData, setMinStockFormData] = useState('10');
  const [showMinStockDialog, setShowMinStockDialog] = useState(false);
  const [productForMinStock, setProductForMinStock] = useState(null);
  const [categoryFormData, setCategoryFormData] = useState({
    name: '',
    description: '',
    color: '#3B82F6',
    markup_coefficient: '1.0',
    min_stock: '',
  });
  const [unitFormData, setUnitFormData] = useState({
    name: '',
    abbreviation: '',
    description: '',
  });

  // Fonction pour formater avec la devise chargée
  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  // Refresh data function using React Query
  const refreshData = async () => {
    try {
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      }
      try {
        const db = await getDB();
        await db.clear('products');
      } catch (error) {
        console.warn('Could not clear IndexedDB:', error);
      }
      await Promise.all([
        refetchProducts(),
        refetchCategories(),
        refetchUnits()
      ]);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  // Obtenir le coefficient de la catégorie sélectionnée
  const getSelectedCategoryCoefficient = () => {
    if (!formData.category_id) return null;
    const category = categories.find(c => c.id === formData.category_id);
    return category?.markup_coefficient || 1.0;
  };

  // Générer automatiquement la référence produit
  // Format: 4 premières lettres + compteur + dernière lettre (tout en majuscule)
  const generateProductReference = (name) => {
    if (!name || name.length < 2) return '';
    
    // Nettoyer le nom (enlever accents et caractères spéciaux)
    const cleanName = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-zA-Z]/g, '');
    
    if (cleanName.length < 2) return '';
    
    // 4 premières lettres (ou moins si nom court)
    const firstPart = cleanName.substring(0, Math.min(4, cleanName.length)).toUpperCase();
    
    // Dernière lettre
    const lastLetter = cleanName.charAt(cleanName.length - 1).toUpperCase();
    
    // Compteur basé sur le nombre total de produits + 1
    const counter = (totalProducts + 1).toString().padStart(3, '0');
    
    return `${firstPart}${counter}${lastLetter}`;
  };

  // Gérer le changement de nom et générer la référence
  const handleNameChange = (name) => {
    const reference = generateProductReference(name);
    setFormData({ 
      ...formData, 
      name: name,
      internal_reference: reference
    });
  };

  // Gérer le changement de catégorie
  const handleCategoryChange = (categoryId) => {
    const actualCategoryId = categoryId === 'none' ? '' : categoryId;
    setFormData({ 
      ...formData, 
      category_id: actualCategoryId
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const productData = {
      name: formData.name,
      internal_reference: formData.internal_reference || null,
      barcode: formData.barcode || null,
      description: formData.description || null,
      category_id: formData.category_id || null,
      unit_id: formData.unit_id || null,
    };

    if (editingProduct) {
      updateProduct.mutate(
        { ...productData, id: editingProduct.id },
        {
          onSuccess: () => {
            setShowDialog(false);
            resetForm();
          },
        }
      );
    } else {
      createProduct.mutate(productData, {
        onSuccess: () => {
          toast.success('Produit ajouté - Ajoutez du stock via un approvisionnement');
          setShowDialog(false);
          resetForm();
        },
      });
    }
  };

  const handleCategorySubmit = async (e) => {
    e.preventDefault();
    
    const categoryData = {
      ...categoryFormData,
      markup_coefficient: parseFloat(categoryFormData.markup_coefficient) || 1.0,
      min_stock: categoryFormData.min_stock !== '' ? parseInt(categoryFormData.min_stock) : null,
    };
    
    if (editingCategory) {
      updateCategory.mutate(
        { categoryId: editingCategory.id, data: categoryData },
        {
          onSuccess: () => {
            resetCategoryForm();
          },
        }
      );
    } else {
      createCategory.mutate(categoryData, {
        onSuccess: () => {
          resetCategoryForm();
        },
      });
    }
  };

  const handleUnitSubmit = async (e) => {
    e.preventDefault();
    
    if (editingUnit) {
      updateUnit.mutate(
        { unitId: editingUnit.id, data: unitFormData },
        {
          onSuccess: () => {
            resetUnitForm();
          },
        }
      );
    } else {
      createUnit.mutate(unitFormData, {
        onSuccess: () => {
          resetUnitForm();
        },
      });
    }
  };

  const handleDelete = (product) => {
    setProductToDelete(product);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!productToDelete) return;
    
    deleteProduct.mutate(productToDelete.id, {
      onSuccess: () => {
        setShowDeleteDialog(false);
        setProductToDelete(null);
      },
      onError: () => {
        setShowDeleteDialog(false);
        setProductToDelete(null);
      },
    });
  };

  const handleToggleStatus = async (product) => {
    toggleProductStatus.mutate(product.id);
  };

  const handleDeleteCategory = (category) => {
    setCategoryToDelete(category);
    setShowDeleteCategoryDialog(true);
  };

  const handleDeleteCategoryConfirm = async () => {
    if (!categoryToDelete) return;
    
    deleteCategory.mutate(categoryToDelete.id, {
      onSuccess: () => {
        setShowDeleteCategoryDialog(false);
        setCategoryToDelete(null);
        if (filterCategory === categoryToDelete.id) {
          setFilterCategory('all');
        }
      },
      onError: () => {
        setShowDeleteCategoryDialog(false);
        setCategoryToDelete(null);
      },
    });
  };

  const handleDeleteUnit = (unit) => {
    setUnitToDelete(unit);
    setShowDeleteUnitDialog(true);
  };

  const handleDeleteUnitConfirm = async () => {
    if (!unitToDelete) return;
    
    deleteUnit.mutate(unitToDelete.id, {
      onSuccess: () => {
        setShowDeleteUnitDialog(false);
        setUnitToDelete(null);
      },
      onError: () => {
        setShowDeleteUnitDialog(false);
        setUnitToDelete(null);
      },
    });
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      internal_reference: product.internal_reference || '',
      barcode: product.barcode || '',
      description: product.description || '',
      category_id: product.category_id || '',
      unit_id: product.unit_id || '',
    });
    setShowDialog(true);
  };

  const handleEditCategory = (category) => {
    setEditingCategory(category);
    setCategoryFormData({
      name: category.name,
      description: category.description || '',
      color: category.color || '#3B82F6',
      markup_coefficient: (category.markup_coefficient || 1.0).toString(),
      min_stock: category.min_stock !== null && category.min_stock !== undefined ? category.min_stock.toString() : '',
    });
  };

  const handleEditUnit = (unit) => {
    setEditingUnit(unit);
    setUnitFormData({
      name: unit.name,
      abbreviation: unit.abbreviation || '',
      description: unit.description || '',
    });
  };

  const resetForm = () => {
    setEditingProduct(null);
    setProductSearchInForm('');
    setFormData({
      name: '',
      internal_reference: '',
      barcode: '',
      description: '',
      category_id: '',
      unit_id: '',
    });
  };

  const resetCategoryForm = () => {
    setEditingCategory(null);
    setCategoryFormData({
      name: '',
      description: '',
      color: '#3B82F6',
      markup_coefficient: '1.0',
      min_stock: '',
    });
  };

  const resetUnitForm = () => {
    setEditingUnit(null);
    setUnitFormData({
      name: '',
      abbreviation: '',
      description: '',
    });
  };

  const getCategoryName = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category?.name || 'Sans catégorie';
  };

  const getCategoryColor = (categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    return category?.color || '#94A3B8';
  };

  const getUnitName = (unitId) => {
    const unit = units.find(u => u.id === unitId);
    return unit?.name || '';
  };

  const getUnitAbbreviation = (unitId) => {
    const unit = units.find(u => u.id === unitId);
    return unit?.abbreviation || unit?.name || '';
  };

  // Calculer si un produit est proche de la péremption
  const isNearExpiration = (product) => {
    if (!product.expiration_date) return false;
    const expDate = new Date(product.expiration_date);
    const now = new Date();
    const daysUntil = Math.ceil((expDate - now) / (1000 * 60 * 60 * 24));
    return daysUntil <= (appSettings.expiration_alert_days || 30) && daysUntil > 0;
  };

  const isExpired = (product) => {
    if (!product.expiration_date) return false;
    const expDate = new Date(product.expiration_date);
    return expDate <= new Date();
  };

  const getDaysUntilExpiration = (product) => {
    if (!product.expiration_date) return 9999;
    const expDate = new Date(product.expiration_date);
    const now = new Date();
    return Math.ceil((expDate - now) / (1000 * 60 * 60 * 24));
  };

  // Utiliser allProducts pour la recherche dans le formulaire
  const filteredProductsInForm = allProducts.filter((p) =>
    productSearchInForm && (
      p.name?.toLowerCase().includes(productSearchInForm.toLowerCase()) ||
      p.barcode?.toLowerCase().includes(productSearchInForm.toLowerCase()) ||
      p.internal_reference?.toLowerCase().includes(productSearchInForm.toLowerCase())
    )
  );

  // Les produits sont déjà filtrés côté serveur par l'API
  // On garde juste le tri côté client pour les priorités visuelles
  const sortedProducts = [...products].sort((a, b) => {
    // 1. Produits à réapprovisionner en premier
    const aLowStock = a.needs_restock || a.stock <= a.min_stock;
    const bLowStock = b.needs_restock || b.stock <= b.min_stock;
    if (aLowStock && !bLowStock) return -1;
    if (!aLowStock && bLowStock) return 1;
    
    // 2. Produits périmés
    const aExpired = isExpired(a);
    const bExpired = isExpired(b);
    if (aExpired && !bExpired) return -1;
    if (!aExpired && bExpired) return 1;
    
    // 3. Produits à péremption proche
    const aNearExp = a.near_expiration || isNearExpiration(a);
    const bNearExp = b.near_expiration || isNearExpiration(b);
    if (aNearExp && !bNearExp) return -1;
    if (!aNearExp && bNearExp) return 1;
    
    // 4. Si les deux sont à péremption proche, trier par date
    if (aNearExp && bNearExp) {
      return (a.days_until_expiration || getDaysUntilExpiration(a)) - (b.days_until_expiration || getDaysUntilExpiration(b));
    }
    
    // 5. Alphabétique (déjà trié côté serveur)
    return 0;
  });

  // Calculer la marge bénéficiaire
  const calculateMargin = (purchasePrice, sellingPrice) => {
    if (!purchasePrice || purchasePrice === 0) return null;
    const margin = ((sellingPrice - purchasePrice) / purchasePrice) * 100;
    return Math.round(margin);
  };

  // Loading state avec skeleton shimmer
  if (productsLoading && products.length === 0) {
    return (
      <Layout>
        <SkeletonProductsPage />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6" data-testid="products-page">
        {/* Header responsive */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mb-1 sm:mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Produits
            </h1>
            <p className="text-sm sm:text-base text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des médicaments • {totalProducts} produit{totalProducts > 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {/* Bouton Gérer les unités */}
            <Dialog open={showUnitDialog} onOpenChange={(open) => { 
              setShowUnitDialog(open); 
              if (!open) {
                resetUnitForm(); 
              }
            }}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  className="rounded-full"
                  disabled={!isWithinScheduledHours}
                  title={!isWithinScheduledHours ? 'Accès restreint - Hors horaires de travail' : ''}
                >
                  <Box className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Unités</span>
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {editingUnit ? 'Modifier l\'unité' : 'Gestion des unités'}
                  </DialogTitle>
                </DialogHeader>
                
                {/* Liste des unités existantes */}
                {!editingUnit && (
                  <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
                    {units.length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-4">Aucune unité</p>
                    ) : (
                      units.map((unit) => (
                        <div key={unit.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                              <Box className="w-4 h-4 text-indigo-600" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900">{unit.name}</p>
                              <p className="text-xs text-slate-500">
                                {unit.abbreviation && <span className="font-mono bg-slate-200 px-1 rounded mr-2">{unit.abbreviation}</span>}
                                {unit.description || 'Aucune description'}
                              </p>
                            </div>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <Button variant="ghost" size="sm" onClick={() => handleEditUnit(unit)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteUnit(unit)} className="text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Formulaire d'ajout/modification d'unité */}
                <form onSubmit={handleUnitSubmit} className="space-y-4 border-t pt-4">
                  <p className="text-sm font-medium text-slate-700">
                    {editingUnit ? 'Modifier' : 'Nouvelle unité'}
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="unit-name">Nom *</Label>
                      <Input
                        id="unit-name"
                        value={unitFormData.name}
                        onChange={(e) => setUnitFormData({ ...unitFormData, name: e.target.value })}
                        required
                        placeholder="Ex: Boîte"
                      />
                    </div>
                    <div>
                      <Label htmlFor="unit-abbr">Abréviation</Label>
                      <Input
                        id="unit-abbr"
                        value={unitFormData.abbreviation}
                        onChange={(e) => setUnitFormData({ ...unitFormData, abbreviation: e.target.value.toUpperCase() })}
                        placeholder="Ex: BTE"
                        className="font-mono"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="unit-desc">Description</Label>
                    <Input
                      id="unit-desc"
                      value={unitFormData.description}
                      onChange={(e) => setUnitFormData({ ...unitFormData, description: e.target.value })}
                      placeholder="Description optionnelle"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    {editingUnit && (
                      <Button type="button" variant="outline" onClick={resetUnitForm}>
                        Annuler
                      </Button>
                    )}
                    <Button type="submit" className="bg-indigo-600 hover:bg-indigo-700">
                      {editingUnit ? 'Mettre à jour' : 'Ajouter'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>

            {/* Bouton Gérer les catégories */}
            <Dialog open={showCategoryDialog} onOpenChange={(open) => { 
              setShowCategoryDialog(open); 
              if (!open) {
                resetCategoryForm(); 
              }
            }}>
              <DialogTrigger asChild>
                <Button 
                  variant="outline" 
                  size="sm"
                  className="rounded-full"
                  disabled={!isWithinScheduledHours}
                  title={!isWithinScheduledHours ? 'Accès restreint - Hors horaires de travail' : ''}
                >
                  <Tag className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Catégories</span>
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-lg">
                <DialogHeader>
                  <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {editingCategory ? 'Modifier la catégorie' : 'Gestion des catégories'}
                  </DialogTitle>
                </DialogHeader>
                
                {/* Liste des catégories existantes */}
                {!editingCategory && (
                  <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
                    {categories.length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-4">Aucune catégorie</p>
                    ) : (
                      categories.map((cat) => (
                        <div key={cat.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div 
                              className="w-4 h-4 rounded-full flex-shrink-0" 
                              style={{ backgroundColor: cat.color || '#3B82F6' }}
                            />
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-slate-900 truncate">{cat.name}</p>
                              <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
                                <span className="flex items-center gap-1">
                                  <Calculator className="w-3 h-3" />
                                  Coef: ×{cat.markup_coefficient || 1.0}
                                </span>
                                {cat.min_stock !== null && cat.min_stock !== undefined && (
                                  <span className="flex items-center gap-1 text-amber-600">
                                    <Package className="w-3 h-3" />
                                    Min: {cat.min_stock}
                                  </span>
                                )}
                                {cat.description && (
                                  <span className="truncate">• {cat.description}</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex gap-1 flex-shrink-0">
                            <Button variant="ghost" size="sm" onClick={() => handleEditCategory(cat)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat)} className="text-red-600">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {/* Formulaire d'ajout/modification */}
                <form onSubmit={handleCategorySubmit} className="space-y-4 border-t pt-4">
                  <p className="text-sm font-medium text-slate-700">
                    {editingCategory ? 'Modifier' : 'Nouvelle catégorie'}
                  </p>
                  <div>
                    <Label htmlFor="cat-name">Nom *</Label>
                    <Input
                      id="cat-name"
                      value={categoryFormData.name}
                      onChange={(e) => setCategoryFormData({ ...categoryFormData, name: e.target.value })}
                      required
                      placeholder="Ex: Antibiotiques"
                    />
                  </div>
                  <div>
                    <Label htmlFor="cat-desc">Description</Label>
                    <Input
                      id="cat-desc"
                      value={categoryFormData.description}
                      onChange={(e) => setCategoryFormData({ ...categoryFormData, description: e.target.value })}
                      placeholder="Description optionnelle"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="cat-color">Couleur</Label>
                      <div className="flex gap-2 items-center mt-1">
                        <input
                          type="color"
                          id="cat-color"
                          value={categoryFormData.color}
                          onChange={(e) => setCategoryFormData({ ...categoryFormData, color: e.target.value })}
                          className="w-10 h-10 rounded cursor-pointer border-0"
                        />
                        <Input
                          value={categoryFormData.color}
                          onChange={(e) => setCategoryFormData({ ...categoryFormData, color: e.target.value })}
                          className="flex-1"
                          placeholder="#3B82F6"
                        />
                      </div>
                    </div>
                    <div>
                      <Label htmlFor="cat-coefficient" className="flex items-center gap-1">
                        <Calculator className="w-3.5 h-3.5 text-teal-600" />
                        Coefficient d'intérêt *
                      </Label>
                      <Input
                        id="cat-coefficient"
                        type="number"
                        step="0.01"
                        min="1"
                        value={categoryFormData.markup_coefficient}
                        onChange={(e) => setCategoryFormData({ ...categoryFormData, markup_coefficient: e.target.value })}
                        required
                        placeholder="1.25"
                        className="mt-1"
                      />
                      <p className="text-xs text-slate-500 mt-1">
                        Prix public = Prix cession × {categoryFormData.markup_coefficient || '1.0'}
                      </p>
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="cat-min-stock" className="flex items-center gap-1">
                      <Package className="w-3.5 h-3.5 text-amber-600" />
                      Stock minimum (optionnel)
                    </Label>
                    <Input
                      id="cat-min-stock"
                      type="number"
                      min="0"
                      value={categoryFormData.min_stock}
                      onChange={(e) => setCategoryFormData({ ...categoryFormData, min_stock: e.target.value })}
                      placeholder="Laisser vide pour utiliser le paramètre global"
                      className="mt-1"
                      data-testid="category-min-stock-input"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Surcharge le stock minimum global pour tous les produits de cette catégorie
                    </p>
                  </div>
                  <div className="flex justify-end gap-2">
                    {editingCategory && (
                      <Button type="button" variant="outline" onClick={resetCategoryForm}>
                        Annuler
                      </Button>
                    )}
                    <Button type="submit" className="bg-teal-700 hover:bg-teal-800">
                      {editingCategory ? 'Mettre à jour' : 'Ajouter'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>

            {/* Bouton Ajouter produit */}
            <Dialog open={showDialog} onOpenChange={(open) => { 
              setShowDialog(open); 
              if (!open) {
                resetForm();
              }
            }}>
              <DialogTrigger asChild>
                <Button 
                  data-testid="add-product-button" 
                  size="sm"
                  className="bg-teal-700 hover:bg-teal-800 rounded-full"
                  disabled={!isWithinScheduledHours}
                  title={!isWithinScheduledHours ? 'Accès restreint - Hors horaires de travail' : ''}
                >
                  <Plus className="w-4 h-4 sm:mr-2" strokeWidth={1.5} />
                  <span className="hidden sm:inline">Ajouter un produit</span>
                  <span className="sm:hidden">Produit</span>
                  {!isOnline && <CloudOff className="w-3 h-3 ml-2 text-amber-300" />}
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {editingProduct ? 'Éditer le produit' : 'Nouveau produit'}
                  </DialogTitle>
                </DialogHeader>
                <form onSubmit={handleSubmit} className="space-y-4" data-testid="product-form">
                  {/* Recherche de produit existant */}
                  {!editingProduct && (
                    <div className="p-3 bg-slate-50 rounded-lg">
                      <Label className="text-sm text-slate-600">Rechercher un produit existant</Label>
                      <div className="relative mt-2">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" strokeWidth={1.5} />
                        <Input
                          placeholder="Nom, code-barres ou référence interne..."
                          value={productSearchInForm}
                          onChange={(e) => setProductSearchInForm(e.target.value)}
                          className="pl-9"
                        />
                      </div>
                      {productSearchInForm && filteredProductsInForm.length > 0 && (
                        <div className="mt-2 max-h-32 overflow-y-auto border border-slate-200 rounded-lg bg-white">
                          {filteredProductsInForm.slice(0, 5).map((product) => (
                            <button
                              key={product.id}
                              type="button"
                              onClick={() => {
                                handleEdit(product);
                                setProductSearchInForm('');
                              }}
                              className="w-full text-left px-3 py-2 hover:bg-slate-50 flex justify-between items-center text-sm"
                            >
                              <div>
                                <p className="font-medium text-slate-900">{product.name}</p>
                                <p className="text-xs text-slate-500">
                                  {product.internal_reference && <span className="mr-2">Réf: {product.internal_reference}</span>}
                                  {product.barcode && <span>Code: {product.barcode}</span>}
                                </p>
                              </div>
                              <span className="text-teal-700 font-medium">{formatAmount(product.price)}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {productSearchInForm && filteredProductsInForm.length === 0 && (
                        <p className="mt-2 text-sm text-slate-500">Aucun produit trouvé - vous pouvez en créer un nouveau</p>
                      )}
                    </div>
                  )}
                  
                  {/* Nom et Référence interne */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="name">Nom du produit *</Label>
                      <Input
                        id="name"
                        value={formData.name}
                        onChange={(e) => handleNameChange(e.target.value)}
                        required
                        data-testid="product-name-input"
                      />
                    </div>
                    <div>
                      <Label htmlFor="internal_reference" className="flex items-center gap-1">
                        <Hash className="w-3.5 h-3.5 text-slate-400" />
                        Référence interne (auto)
                      </Label>
                      <Input
                        id="internal_reference"
                        value={formData.internal_reference}
                        readOnly
                        disabled
                        className="mt-1 bg-slate-100 text-slate-500 cursor-not-allowed"
                        data-testid="product-reference-input"
                        placeholder="Ex: MED-001"
                      />
                    </div>
                  </div>

                  {/* Code-barres */}
                  <div>
                    <Label htmlFor="barcode">Code-barres</Label>
                    <Input
                      id="barcode"
                      value={formData.barcode}
                      onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
                      data-testid="product-barcode-input"
                    />
                  </div>

                  {/* Description */}
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>

                  {/* Catégorie et Unité */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="category">Catégorie</Label>
                      <Select 
                        value={formData.category_id || 'none'} 
                        onValueChange={handleCategoryChange}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionner une catégorie" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Sans catégorie</SelectItem>
                          {categories.map((cat) => (
                            <SelectItem key={cat.id} value={cat.id}>
                              <div className="flex items-center gap-2">
                                <div 
                                  className="w-3 h-3 rounded-full" 
                                  style={{ backgroundColor: cat.color || '#3B82F6' }}
                                />
                                {cat.name}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {formData.category_id && (
                        <p className="text-xs text-teal-600 mt-1 flex items-center gap-1">
                          <Calculator className="w-3 h-3" />
                          Le prix public sera calculé automatiquement
                        </p>
                      )}
                    </div>
                    <div>
                      <Label htmlFor="unit">Unité</Label>
                      <Select 
                        value={formData.unit_id || 'none'} 
                        onValueChange={(value) => setFormData({ ...formData, unit_id: value === 'none' ? '' : value })}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Sélectionner une unité" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="none">Sans unité</SelectItem>
                          {units.map((unit) => (
                            <SelectItem key={unit.id} value={unit.id}>
                              <div className="flex items-center gap-2">
                                <Box className="w-3 h-3 text-indigo-500" />
                                {unit.name}
                                {unit.abbreviation && (
                                  <span className="text-xs text-slate-400 font-mono">({unit.abbreviation})</span>
                                )}
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {/* Information sur les prix et stocks */}
                  <div className="p-4 bg-gradient-to-r from-amber-50 to-orange-50 rounded-lg border border-amber-200">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      <span className="font-medium text-amber-800">Prix et Stock</span>
                    </div>
                    <p className="text-sm text-amber-700">
                      Les prix de cession, prix public, stock et dates de péremption sont gérés automatiquement lors des <strong>approvisionnements</strong>.
                    </p>
                    <p className="text-xs text-amber-600 mt-2">
                      Après avoir créé le produit, ajoutez du stock via le menu "Approvisionnements".
                    </p>
                  </div>

                  <div className="flex justify-end gap-3 pt-4">
                    <Button type="button" variant="outline" onClick={() => { setShowDialog(false); resetForm(); }}>
                      Annuler
                    </Button>
                    <Button type="submit" data-testid="product-submit-button" className="bg-teal-700 hover:bg-teal-800">
                      {editingProduct ? 'Mettre à jour' : 'Ajouter'}
                    </Button>
                  </div>
                </form>
              </DialogContent>
            </Dialog>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
            <Input
              placeholder="Rechercher par nom, code-barres ou référence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              data-testid="product-search-input"
              className="pl-10"
              disabled={!isWithinScheduledHours}
            />
          </div>
          <Select value={filterCategory} onValueChange={setFilterCategory} disabled={!isWithinScheduledHours}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Filtrer par catégorie" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Toutes les catégories</SelectItem>
              {categories.map((cat) => (
                <SelectItem key={cat.id} value={cat.id}>
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: cat.color || '#3B82F6' }}
                    />
                    {cat.name}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {isAdmin && (
            <Select value={filterStatus} onValueChange={setFilterStatus} disabled={!isWithinScheduledHours}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filtrer par statut" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous les statuts</SelectItem>
                <SelectItem value="active">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-500" />
                    Actifs
                  </div>
                </SelectItem>
                <SelectItem value="inactive">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    Désactivés
                  </div>
                </SelectItem>
                <SelectItem value="low_stock">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-3 h-3 text-amber-500" />
                    Stock bas
                  </div>
                </SelectItem>
                <SelectItem value="near_expiration">
                  <div className="flex items-center gap-2">
                    <Clock className="w-3 h-3 text-orange-500" />
                    Péremption proche
                  </div>
                </SelectItem>
                <SelectItem value="expired">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-3 h-3 text-red-500" />
                    Périmés
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          )}
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
                  {shiftEligibility?.reason || 'Vous ne pouvez pas accéder aux produits en dehors de vos horaires planifiés.'}
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
        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedProducts.map((product) => {
            const needsRestock = product.needs_restock || product.stock <= product.min_stock;
            const margin = calculateMargin(product.purchase_price, product.price);
            const nearExp = product.near_expiration || isNearExpiration(product);
            const expired = isExpired(product);
            const daysUntil = product.days_until_expiration || getDaysUntilExpiration(product);
            const isPending = product._offline || product._pendingSync;
            return (
            <div
              key={product.id}
              data-testid={`product-card-${product.id}`}
              className={`p-4 rounded-xl bg-white border transition-all cursor-pointer ${
                isPending
                  ? 'border-amber-300 bg-amber-50/30'
                  : product.is_active === false 
                    ? 'border-red-200 bg-red-50/30 opacity-75' 
                    : expired
                      ? 'border-red-400 bg-red-50/50'
                      : nearExp
                        ? 'border-orange-300 bg-orange-50/30'
                        : needsRestock
                          ? 'border-amber-300 bg-amber-50/30'
                          : 'border-slate-100 hover:border-teal-200'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h3 className="font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {product.name}
                    </h3>
                    {isPending && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium flex items-center gap-1">
                        <CloudOff className="w-3 h-3" />
                        Non sync
                      </span>
                    )}
                    {product.is_active === false && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                        Désactivé
                      </span>
                    )}
                    {expired && product.is_active !== false && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Périmé
                      </span>
                    )}
                    {nearExp && !expired && product.is_active !== false && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 font-medium flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {daysUntil}j
                      </span>
                    )}
                    {needsRestock && product.is_active !== false && !expired && !isPending && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3" />
                        Réappro.
                      </span>
                    )}
                  </div>
                  {/* Référence interne et code-barres */}
                  <div className="flex flex-wrap gap-2 text-xs text-slate-500" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                    {product.internal_reference && (
                      <span className="flex items-center gap-1 bg-slate-100 px-1.5 py-0.5 rounded">
                        <Hash className="w-3 h-3" />
                        {product.internal_reference}
                      </span>
                    )}
                    {product.barcode && (
                      <span className="bg-slate-100 px-1.5 py-0.5 rounded">
                        {product.barcode}
                      </span>
                    )}
                  </div>
                </div>
                <div className={`p-2 rounded-lg ${
                  expired ? 'bg-red-100' : 
                  nearExp ? 'bg-orange-100' : 
                  needsRestock && product.is_active !== false ? 'bg-amber-100' : 'bg-teal-50'
                }`}>
                  {expired ? (
                    <Calendar className="w-5 h-5 text-red-600" strokeWidth={1.5} />
                  ) : nearExp ? (
                    <Clock className="w-5 h-5 text-orange-600" strokeWidth={1.5} />
                  ) : needsRestock && product.is_active !== false ? (
                    <AlertTriangle className="w-5 h-5 text-amber-600" strokeWidth={1.5} />
                  ) : (
                    <Package className="w-5 h-5 text-teal-700" strokeWidth={1.5} />
                  )}
                </div>
              </div>
              
              {/* Category and Unit Badges */}
              <div className="flex flex-wrap gap-2 mb-3">
                {product.category_id && (
                  <span 
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: getCategoryColor(product.category_id) }}
                  >
                    <Tag className="w-3 h-3" />
                    {getCategoryName(product.category_id)}
                  </span>
                )}
                {product.unit_id && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                    <Box className="w-3 h-3" />
                    {getUnitAbbreviation(product.unit_id) || getUnitName(product.unit_id)}
                  </span>
                )}
              </div>
              
              <div className="space-y-2 mb-3">
                {product.purchase_price > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">Cession:</span>
                    <span className="text-slate-600">{formatAmount(product.purchase_price)}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Public:</span>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-900">{formatAmount(product.price)}</span>
                    {margin !== null && margin > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">
                        +{margin}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Stock:</span>
                  <span className={`font-medium ${product.stock <= product.min_stock ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {product.stock} {product.unit_id ? getUnitAbbreviation(product.unit_id).toLowerCase() : 'unités'}
                  </span>
                </div>
                {product.expiration_date && (
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-600">Péremption:</span>
                    <span className={`font-medium flex items-center gap-1 ${
                      expired ? 'text-red-600' : nearExp ? 'text-orange-600' : 'text-slate-600'
                    }`}>
                      <Calendar className="w-3 h-3" />
                      {new Date(product.expiration_date).toLocaleDateString('fr-FR')}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleEdit(product)}
                  data-testid={`edit-product-${product.id}`}
                  className="flex-1"
                >
                  <Edit className="w-4 h-4 mr-1" strokeWidth={1.5} />
                  Éditer
                </Button>
                {isAdmin && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleStatus(product)}
                    data-testid={`toggle-product-${product.id}`}
                    className={product.is_active === false 
                      ? "text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50" 
                      : "text-amber-600 hover:text-amber-700 hover:bg-amber-50"
                    }
                    title={product.is_active === false ? "Activer le produit" : "Désactiver le produit"}
                  >
                    {product.is_active === false ? (
                      <Power className="w-4 h-4" strokeWidth={1.5} />
                    ) : (
                      <PowerOff className="w-4 h-4" strokeWidth={1.5} />
                    )}
                  </Button>
                )}
                {/* Bouton suppression - Admin uniquement */}
                {user?.role === 'admin' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(product)}
                    data-testid={`delete-product-${product.id}`}
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                  >
                    <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                  </Button>
                )}
              </div>
            </div>
          );
          })}
        </div>

        {/* Infinite Scroll Info & Loader */}
        {products.length > 0 && (
          <div className="flex flex-col items-center gap-4 py-6">
            <p className="text-sm text-slate-600">
              {products.length} sur {totalProducts} produits affichés
            </p>
            
            {/* Élément observé pour le chargement automatique */}
            <div ref={loadMoreRef} className="h-2 w-full" />
            
            {/* Indicateur de chargement */}
            {isFetchingNextPage && (
              <div className="flex items-center gap-2 text-teal-600">
                <Loader2 className="w-5 h-5 animate-spin" />
                <span className="text-sm">Chargement...</span>
              </div>
            )}
            
            {/* Bouton Charger plus (fallback si l'observer ne fonctionne pas) */}
            {hasNextPage && !isFetchingNextPage && (
              <Button 
                variant="outline" 
                onClick={() => fetchNextPage()}
                className="rounded-full"
              >
                Charger plus de produits
              </Button>
            )}
            
            {/* Fin de la liste */}
            {!hasNextPage && products.length > 0 && (
              <p className="text-sm text-slate-400">
                ✓ Tous les produits ont été chargés
              </p>
            )}
          </div>
        )}

        {products.length === 0 && !productsLoading && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500">
              Aucun produit trouvé
            </p>
          </div>
        )}
        </>
        )}
      </div>

      {/* Dialogue de confirmation de suppression produit */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer le produit "{productToDelete?.name}" ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowDeleteDialog(false); setProductToDelete(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} className="bg-red-600 hover:bg-red-700">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialogue de confirmation de suppression catégorie */}
      <AlertDialog open={showDeleteCategoryDialog} onOpenChange={setShowDeleteCategoryDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer la catégorie</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer la catégorie "{categoryToDelete?.name}" ?
              Les produits associés ne seront pas supprimés mais n'auront plus de catégorie.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowDeleteCategoryDialog(false); setCategoryToDelete(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteCategoryConfirm} className="bg-red-600 hover:bg-red-700">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialogue de confirmation de suppression unité */}
      <AlertDialog open={showDeleteUnitDialog} onOpenChange={setShowDeleteUnitDialog}>
        <AlertDialogContent className="bg-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer l'unité</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer l'unité "{unitToDelete?.name}" ?
              Cette action n'est possible que si aucun produit n'utilise cette unité.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setShowDeleteUnitDialog(false); setUnitToDelete(null); }}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteUnitConfirm} className="bg-red-600 hover:bg-red-700">
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Products;
