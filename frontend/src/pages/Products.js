import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious, PaginationEllipsis } from '../components/ui/pagination';
import { Plus, Search, Edit, Trash2, Package, Tag, Settings, Power, PowerOff, AlertTriangle, Calculator, TrendingUp, Box, Hash, Calendar, Clock } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems, updateItem, deleteItem as deleteFromDB, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Products = () => {
  const { user } = useAuth();
  const [appSettings, setAppSettings] = useState({ currency: 'GNF', expiration_alert_days: 30 });
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [units, setUnits] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [showCategoryDialog, setShowCategoryDialog] = useState(false);
  const [showUnitDialog, setShowUnitDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  const [editingUnit, setEditingUnit] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [productsPerPage] = useState(9);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showDeleteCategoryDialog, setShowDeleteCategoryDialog] = useState(false);
  const [showDeleteUnitDialog, setShowDeleteUnitDialog] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [unitToDelete, setUnitToDelete] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [productSearchInForm, setProductSearchInForm] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    internal_reference: '',
    barcode: '',
    description: '',
    purchase_price: '',
    price: '',
    stock: '',
    min_stock: '10',
    category_id: '',
    unit_id: '',
    expiration_date: '',
  });
  const [categoryFormData, setCategoryFormData] = useState({
    name: '',
    description: '',
    color: '#3B82F6',
    markup_coefficient: '1.0',
  });
  const [unitFormData, setUnitFormData] = useState({
    name: '',
    abbreviation: '',
    description: '',
  });
  const { isOnline } = useOffline();

  // Charger les settings
  const loadAppSettings = async () => {
    try {
      const response = await api.get('/settings');
      setAppSettings(response.data);
    } catch (error) {
      console.error('Error loading settings:', error);
    }
  };

  // Fonction pour formater avec la devise chargée
  const formatAmount = (amount) => {
    const currency = appSettings?.currency || 'EUR';
    const symbols = { USD: '$', CAD: '$ CAD', EUR: '€', XOF: 'FCFA', GNF: 'GNF' };
    const decimals = { USD: 2, CAD: 2, EUR: 2, XOF: 0, GNF: 0 };
    const dec = decimals[currency] ?? 2;
    const formatted = (amount || 0).toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
    return `${formatted} ${symbols[currency] || currency}`;
  };

  const loadCategories = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        const timestamp = Date.now();
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' } : {};
        const response = await api.get(`/categories?_t=${timestamp}`, { headers });
        setCategories(response.data);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const loadUnits = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        const timestamp = Date.now();
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' } : {};
        const response = await api.get(`/units?_t=${timestamp}`, { headers });
        setUnits(response.data);
      }
    } catch (error) {
      console.error('Error loading units:', error);
    }
  };

  const loadProducts = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache' } : {};
        const response = await api.get('/products', { headers });
        setProducts(response.data);
        
        if (forceRefresh) {
          try {
            const db = await getDB();
            await db.clear('products');
          } catch (error) {
            console.warn('Could not clear IndexedDB:', error);
          }
        }
        
        for (const product of response.data) {
          await addItem('products', product);
        }
      } else {
        const localProducts = await getAllItems('products');
        setProducts(localProducts);
      }
    } catch (error) {
      console.error('Error loading products:', error);
      const localProducts = await getAllItems('products');
      setProducts(localProducts);
    }
  };

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
        loadProducts(true),
        loadCategories(true),
        loadUnits(true)
      ]);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  useEffect(() => {
    const init = async () => {
      await loadAppSettings();
      await loadProducts();
      await loadCategories();
      await loadUnits();
    };
    init();
  }, []); // eslint-disable-line

  // Obtenir le coefficient de la catégorie sélectionnée
  const getSelectedCategoryCoefficient = () => {
    if (!formData.category_id) return null;
    const category = categories.find(c => c.id === formData.category_id);
    return category?.markup_coefficient || 1.0;
  };

  // Calculer le prix de vente automatiquement
  const calculateSellingPrice = (purchasePrice, categoryId) => {
    const category = categories.find(c => c.id === categoryId);
    const coefficient = category?.markup_coefficient || 1.0;
    return Math.round(purchasePrice * coefficient * 100) / 100;
  };

  // Gérer le changement de prix d'achat
  const handlePurchasePriceChange = (value) => {
    const purchasePrice = parseFloat(value) || 0;
    const sellingPrice = calculateSellingPrice(purchasePrice, formData.category_id);
    setFormData({ 
      ...formData, 
      purchase_price: value,
      price: sellingPrice.toString()
    });
  };

  // Gérer le changement de catégorie (recalculer le prix de vente)
  const handleCategoryChange = (categoryId) => {
    const purchasePrice = parseFloat(formData.purchase_price) || 0;
    const actualCategoryId = categoryId === 'none' ? '' : categoryId;
    const sellingPrice = calculateSellingPrice(purchasePrice, actualCategoryId);
    setFormData({ 
      ...formData, 
      category_id: actualCategoryId,
      price: sellingPrice.toString()
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const productData = {
        ...formData,
        internal_reference: formData.internal_reference || null,
        purchase_price: parseFloat(formData.purchase_price) || 0,
        price: parseFloat(formData.price),
        stock: parseInt(formData.stock),
        min_stock: parseInt(formData.min_stock),
        category_id: formData.category_id || null,
        unit_id: formData.unit_id || null,
        expiration_date: formData.expiration_date || null,
      };

      if (editingProduct) {
        if (isOnline) {
          await api.put(`/products/${editingProduct.id}`, productData);
          toast.success('Produit mis à jour');
          setShowDialog(false);
          resetForm();
          await refreshData();
        } else {
          productData.id = editingProduct.id;
          await updateItem('products', productData);
          await addLocalChange('products', 'update', productData);
          toast.success('Produit mis à jour (synchronisation en attente)');
          setShowDialog(false);
          resetForm();
          await loadProducts();
        }
      } else {
        if (isOnline) {
          await api.post('/products', productData);
          toast.success('Produit ajouté');
          setShowDialog(false);
          resetForm();
          await refreshData();
        } else {
          const newProductId = crypto.randomUUID();
          const newProduct = { ...productData, id: newProductId };
          await addItem('products', newProduct);
          await addLocalChange('products', 'create', newProduct);
          toast.success('Produit ajouté (synchronisation en attente)');
          setShowDialog(false);
          resetForm();
          await loadProducts();
        }
      }
    } catch (error) {
      console.error('Error saving product:', error);
      const errorMessage = error.response?.data?.detail || 'Erreur lors de l\'enregistrement';
      toast.error(errorMessage);
    }
  };

  const handleCategorySubmit = async (e) => {
    e.preventDefault();
    
    try {
      const categoryData = {
        ...categoryFormData,
        markup_coefficient: parseFloat(categoryFormData.markup_coefficient) || 1.0,
      };
      
      if (editingCategory) {
        await api.put(`/categories/${editingCategory.id}`, categoryData);
        toast.success('Catégorie mise à jour');
      } else {
        await api.post('/categories', categoryData);
        toast.success('Catégorie ajoutée');
      }
      resetCategoryForm();
      await new Promise(resolve => setTimeout(resolve, 100));
      await loadCategories(true);
    } catch (error) {
      console.error('Error saving category:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'enregistrement de la catégorie');
    }
  };

  const handleUnitSubmit = async (e) => {
    e.preventDefault();
    
    try {
      if (editingUnit) {
        await api.put(`/units/${editingUnit.id}`, unitFormData);
        toast.success('Unité mise à jour');
      } else {
        await api.post('/units', unitFormData);
        toast.success('Unité ajoutée');
      }
      resetUnitForm();
      await new Promise(resolve => setTimeout(resolve, 100));
      await loadUnits(true);
    } catch (error) {
      console.error('Error saving unit:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de l\'enregistrement de l\'unité');
    }
  };

  const handleDelete = (product) => {
    setProductToDelete(product);
    setShowDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!productToDelete) return;
    
    try {
      if (isOnline) {
        await api.delete(`/products/${productToDelete.id}`);
        toast.success('Produit supprimé');
        await refreshData();
      } else {
        await deleteFromDB('products', productToDelete.id);
        await addLocalChange('products', 'delete', { id: productToDelete.id });
        toast.success('Produit supprimé (synchronisation en attente)');
        await loadProducts();
      }
      setShowDeleteDialog(false);
      setProductToDelete(null);
    } catch (error) {
      console.error('Error deleting product:', error);
      const errorMessage = error.response?.data?.detail || 'Erreur lors de la suppression';
      toast.error(errorMessage);
      setShowDeleteDialog(false);
      setProductToDelete(null);
    }
  };

  const handleToggleStatus = async (product) => {
    try {
      const response = await api.patch(`/products/${product.id}/toggle-status`);
      toast.success(response.data.message);
      await refreshData();
    } catch (error) {
      console.error('Error toggling product status:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors du changement de statut');
    }
  };

  const handleDeleteCategory = (category) => {
    setCategoryToDelete(category);
    setShowDeleteCategoryDialog(true);
  };

  const handleDeleteCategoryConfirm = async () => {
    if (!categoryToDelete) return;
    
    try {
      await api.delete(`/categories/${categoryToDelete.id}`);
      toast.success('Catégorie supprimée');
      setShowDeleteCategoryDialog(false);
      setCategoryToDelete(null);
      if (filterCategory === categoryToDelete.id) {
        setFilterCategory('all');
      }
      await loadCategories(true);
    } catch (error) {
      console.error('Error deleting category:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const handleDeleteUnit = (unit) => {
    setUnitToDelete(unit);
    setShowDeleteUnitDialog(true);
  };

  const handleDeleteUnitConfirm = async () => {
    if (!unitToDelete) return;
    
    try {
      await api.delete(`/units/${unitToDelete.id}`);
      toast.success('Unité supprimée');
      setShowDeleteUnitDialog(false);
      setUnitToDelete(null);
      await loadUnits(true);
    } catch (error) {
      console.error('Error deleting unit:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      internal_reference: product.internal_reference || '',
      barcode: product.barcode || '',
      description: product.description || '',
      purchase_price: (product.purchase_price || 0).toString(),
      price: product.price.toString(),
      stock: product.stock.toString(),
      min_stock: product.min_stock.toString(),
      category_id: product.category_id || '',
      unit_id: product.unit_id || '',
      expiration_date: product.expiration_date ? product.expiration_date.split('T')[0] : '',
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
      purchase_price: '',
      price: '',
      stock: '',
      min_stock: '10',
      category_id: '',
      unit_id: '',
      expiration_date: '',
    });
  };

  const resetCategoryForm = () => {
    setEditingCategory(null);
    setCategoryFormData({
      name: '',
      description: '',
      color: '#3B82F6',
      markup_coefficient: '1.0',
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

  const isAdmin = user?.role === 'admin';

  const filteredProductsInForm = products.filter((p) =>
    productSearchInForm && (
      p.name?.toLowerCase().includes(productSearchInForm.toLowerCase()) ||
      p.barcode?.toLowerCase().includes(productSearchInForm.toLowerCase()) ||
      p.internal_reference?.toLowerCase().includes(productSearchInForm.toLowerCase())
    )
  );

  const filteredProducts = products
    .filter((p) => {
      const matchesSearch = p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.barcode?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.internal_reference?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = filterCategory === 'all' || p.category_id === filterCategory;
      const matchesStatus = filterStatus === 'all' || 
        (filterStatus === 'active' && p.is_active !== false) || 
        (filterStatus === 'inactive' && p.is_active === false);
      return matchesSearch && matchesCategory && matchesStatus;
    })
    .sort((a, b) => {
      const aLowStock = a.stock <= a.min_stock;
      const bLowStock = b.stock <= b.min_stock;
      if (aLowStock && !bLowStock) return -1;
      if (!aLowStock && bLowStock) return 1;
      return a.name.localeCompare(b.name);
    });

  const totalPages = Math.ceil(filteredProducts.length / productsPerPage);
  const startIndex = (currentPage - 1) * productsPerPage;
  const endIndex = startIndex + productsPerPage;
  const currentProducts = filteredProducts.slice(startIndex, endIndex);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, filterCategory]);

  // Calculer la marge bénéficiaire
  const calculateMargin = (purchasePrice, sellingPrice) => {
    if (!purchasePrice || purchasePrice === 0) return null;
    const margin = ((sellingPrice - purchasePrice) / purchasePrice) * 100;
    return Math.round(margin);
  };

  return (
    <Layout>
      <div className="space-y-6" data-testid="products-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Produits
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des médicaments et produits • {products.length} produit{products.length > 1 ? 's' : ''}
            </p>
          </div>
          <div className="flex gap-2">
            {/* Bouton Gérer les unités */}
            <Dialog open={showUnitDialog} onOpenChange={(open) => { 
              setShowUnitDialog(open); 
              if (open) {
                loadUnits(true);
              } else {
                resetUnitForm(); 
              }
            }}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-full">
                  <Box className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Unités
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
              if (open) {
                loadCategories(true);
              } else {
                resetCategoryForm(); 
              }
            }}>
              <DialogTrigger asChild>
                <Button variant="outline" className="rounded-full">
                  <Tag className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Catégories
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
                              <div className="flex items-center gap-2 text-xs text-slate-500">
                                <span className="flex items-center gap-1">
                                  <Calculator className="w-3 h-3" />
                                  Coef: ×{cat.markup_coefficient || 1.0}
                                </span>
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
                        Prix vente = Prix achat × {categoryFormData.markup_coefficient || '1.0'}
                      </p>
                    </div>
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
              if (open) {
                loadCategories();
                loadUnits();
              } else {
                resetForm();
              }
            }}>
              <DialogTrigger asChild>
                <Button data-testid="add-product-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                  <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                  Ajouter un produit
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
                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        required
                        data-testid="product-name-input"
                      />
                    </div>
                    <div>
                      <Label htmlFor="internal_reference" className="flex items-center gap-1">
                        <Hash className="w-3.5 h-3.5 text-slate-400" />
                        Référence interne
                      </Label>
                      <Input
                        id="internal_reference"
                        value={formData.internal_reference}
                        onChange={(e) => setFormData({ ...formData, internal_reference: e.target.value.toUpperCase() })}
                        data-testid="product-reference-input"
                        placeholder="Ex: MED-001"
                        className="font-mono"
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
                          Le prix de vente sera calculé automatiquement
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

                  {/* Prix */}
                  <div className="p-4 bg-gradient-to-r from-teal-50 to-emerald-50 rounded-lg border border-teal-100">
                    <div className="flex items-center gap-2 mb-3">
                      <TrendingUp className="w-4 h-4 text-teal-700" />
                      <span className="font-medium text-teal-800">Calcul du prix</span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="purchase_price" className="text-slate-700">Prix d'achat (fournisseur) *</Label>
                        <Input
                          id="purchase_price"
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.purchase_price}
                          onChange={(e) => handlePurchasePriceChange(e.target.value)}
                          required
                          data-testid="product-purchase-price-input"
                          className="bg-white"
                          placeholder="0.00"
                        />
                      </div>
                      <div>
                        <Label htmlFor="price" className="text-slate-700">Prix de vente *</Label>
                        <Input
                          id="price"
                          type="number"
                          step="0.01"
                          min="0"
                          value={formData.price}
                          onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                          required
                          data-testid="product-price-input"
                          className="bg-white"
                          placeholder="0.00"
                        />
                        {formData.purchase_price && formData.price && (
                          <p className="text-xs text-emerald-600 mt-1">
                            Marge: +{calculateMargin(parseFloat(formData.purchase_price), parseFloat(formData.price))}%
                          </p>
                        )}
                      </div>
                    </div>
                    {formData.category_id && formData.purchase_price && (
                      <p className="text-xs text-slate-600 mt-2">
                        💡 Prix suggéré: {formatAmount(calculateSellingPrice(parseFloat(formData.purchase_price), formData.category_id))}
                      </p>
                    )}
                  </div>

                  {/* Stock */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="stock">Stock actuel *</Label>
                      <Input
                        id="stock"
                        type="number"
                        value={formData.stock}
                        onChange={(e) => setFormData({ ...formData, stock: e.target.value })}
                        required
                        data-testid="product-stock-input"
                      />
                    </div>
                    <div>
                      <Label htmlFor="min_stock">Stock minimum *</Label>
                      <Input
                        id="min_stock"
                        type="number"
                        value={formData.min_stock}
                        onChange={(e) => setFormData({ ...formData, min_stock: e.target.value })}
                        required
                      />
                    </div>
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
            />
          </div>
          <Select value={filterCategory} onValueChange={setFilterCategory}>
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
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-[160px]">
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
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {currentProducts.map((product) => {
            const needsRestock = product.stock <= product.min_stock;
            const margin = calculateMargin(product.purchase_price, product.price);
            return (
            <div
              key={product.id}
              data-testid={`product-card-${product.id}`}
              className={`p-4 rounded-xl bg-white border transition-all cursor-pointer ${
                product.is_active === false 
                  ? 'border-red-200 bg-red-50/30 opacity-75' 
                  : needsRestock
                    ? 'border-amber-300 bg-amber-50/30'
                    : 'border-slate-100 hover:border-teal-200'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-slate-900" style={{ fontFamily: 'Manrope, sans-serif' }}>
                      {product.name}
                    </h3>
                    {product.is_active === false && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                        Désactivé
                      </span>
                    )}
                    {needsRestock && product.is_active !== false && (
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
                <div className={`p-2 rounded-lg ${needsRestock && product.is_active !== false ? 'bg-amber-100' : 'bg-teal-50'}`}>
                  {needsRestock && product.is_active !== false ? (
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
                    <span className="text-slate-500">Achat:</span>
                    <span className="text-slate-600">{formatAmount(product.purchase_price)}</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Vente:</span>
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
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(product)}
                  data-testid={`delete-product-${product.id}`}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" strokeWidth={1.5} />
                </Button>
              </div>
            </div>
          );
          })}
        </div>

        {/* Pagination Info */}
        {filteredProducts.length > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600">
              Affichage de {startIndex + 1} à {Math.min(endIndex, filteredProducts.length)} sur {filteredProducts.length} produits
            </p>
            <div className="text-sm text-slate-600">
              Page {currentPage} sur {totalPages}
            </div>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious 
                  onClick={() => handlePageChange(Math.max(currentPage - 1, 1))}
                  className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>
              
              {[...Array(totalPages)].map((_, index) => {
                const pageNumber = index + 1;
                const showPage = 
                  pageNumber === 1 || 
                  pageNumber === totalPages || 
                  (pageNumber >= currentPage - 1 && pageNumber <= currentPage + 1);
                
                if (!showPage && pageNumber === 2 && currentPage > 4) {
                  return (
                    <PaginationItem key="ellipsis1">
                      <PaginationEllipsis />
                    </PaginationItem>
                  );
                }
                
                if (!showPage && pageNumber === totalPages - 1 && currentPage < totalPages - 3) {
                  return (
                    <PaginationItem key="ellipsis2">
                      <PaginationEllipsis />
                    </PaginationItem>
                  );
                }
                
                if (!showPage) return null;
                
                return (
                  <PaginationItem key={pageNumber}>
                    <PaginationLink
                      onClick={() => handlePageChange(pageNumber)}
                      isActive={currentPage === pageNumber}
                      className="cursor-pointer"
                    >
                      {pageNumber}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}
              
              <PaginationItem>
                <PaginationNext 
                  onClick={() => handlePageChange(Math.min(currentPage + 1, totalPages))}
                  className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        )}

        {filteredProducts.length === 0 && (
          <div className="text-center py-12 bg-white rounded-2xl border border-slate-200">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-3" strokeWidth={1.5} />
            <p className="text-slate-500">
              Aucun produit trouvé
            </p>
          </div>
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
