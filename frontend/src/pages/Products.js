import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../components/ui/alert-dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious, PaginationEllipsis } from '../components/ui/pagination';
import { Plus, Search, Edit, Trash2, Package, Tag, Settings, Power, PowerOff } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems, updateItem, deleteItem as deleteFromDB, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { useAuth } from '../contexts/AuthContext';
import { toast } from 'sonner';

const Products = () => {
  const { user } = useAuth();
  const [appSettings, setAppSettings] = useState({ currency: 'GNF' });
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [showCategoryDialog, setShowCategoryDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editingCategory, setEditingCategory] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [productsPerPage] = useState(9);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showDeleteCategoryDialog, setShowDeleteCategoryDialog] = useState(false);
  const [productToDelete, setProductToDelete] = useState(null);
  const [categoryToDelete, setCategoryToDelete] = useState(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all'); // all, active, inactive
  const [productSearchInForm, setProductSearchInForm] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    barcode: '',
    description: '',
    price: '',
    stock: '',
    min_stock: '10',
    category_id: '',
  });
  const [categoryFormData, setCategoryFormData] = useState({
    name: '',
    description: '',
    color: '#3B82F6',
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
        const timestamp = Date.now(); // Cache buster
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache', 'Pragma': 'no-cache' } : {};
        const response = await api.get(`/categories?_t=${timestamp}`, { headers });
        console.log('Categories loaded:', response.data.length);
        setCategories(response.data);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
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
        loadCategories(true)
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
    };
    init();
  }, []); // eslint-disable-line

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const productData = {
        ...formData,
        price: parseFloat(formData.price),
        stock: parseInt(formData.stock),
        min_stock: parseInt(formData.min_stock),
        category_id: formData.category_id || null,
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
      if (editingCategory) {
        await api.put(`/categories/${editingCategory.id}`, categoryFormData);
        toast.success('Catégorie mise à jour');
      } else {
        await api.post('/categories', categoryFormData);
        toast.success('Catégorie ajoutée');
      }
      resetCategoryForm();
      // Attendre un instant pour s'assurer que le backend a enregistré
      await new Promise(resolve => setTimeout(resolve, 100));
      // Recharger les catégories avec force refresh
      await loadCategories(true);
      // Ne pas fermer le dialogue pour permettre d'ajouter plusieurs catégories
    } catch (error) {
      console.error('Error saving category:', error);
      toast.error('Erreur lors de l\'enregistrement de la catégorie');
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
      // Afficher le message d'erreur du serveur (règle d'affaires)
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
      // Reset filter if deleted category was selected
      if (filterCategory === categoryToDelete.id) {
        setFilterCategory('all');
      }
      await loadCategories(true); // Force refresh avec nouvelle référence
    } catch (error) {
      console.error('Error deleting category:', error);
      toast.error(error.response?.data?.detail || 'Erreur lors de la suppression');
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name,
      barcode: product.barcode || '',
      description: product.description || '',
      price: product.price.toString(),
      stock: product.stock.toString(),
      min_stock: product.min_stock.toString(),
      category_id: product.category_id || '',
    });
    setShowDialog(true);
  };

  const handleEditCategory = (category) => {
    setEditingCategory(category);
    setCategoryFormData({
      name: category.name,
      description: category.description || '',
      color: category.color || '#3B82F6',
    });
    setShowCategoryDialog(true);
  };

  const resetForm = () => {
    setEditingProduct(null);
    setProductSearchInForm('');
    setFormData({
      name: '',
      barcode: '',
      description: '',
      price: '',
      stock: '',
      min_stock: '10',
      category_id: '',
    });
  };

  const resetCategoryForm = () => {
    setEditingCategory(null);
    setCategoryFormData({
      name: '',
      description: '',
      color: '#3B82F6',
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

  const isAdmin = user?.role === 'admin';

  // Filtrage pour la recherche dans le formulaire produit
  const filteredProductsInForm = products.filter((p) =>
    productSearchInForm && (
      p.name?.toLowerCase().includes(productSearchInForm.toLowerCase()) ||
      p.barcode?.toLowerCase().includes(productSearchInForm.toLowerCase())
    )
  );

  const filteredProducts = products
    .filter((p) => {
      const matchesSearch = p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.barcode?.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = filterCategory === 'all' || p.category_id === filterCategory;
      const matchesStatus = filterStatus === 'all' || 
        (filterStatus === 'active' && p.is_active !== false) || 
        (filterStatus === 'inactive' && p.is_active === false);
      return matchesSearch && matchesCategory && matchesStatus;
    })
    // Trier: produits nécessitant réapprovisionnement en premier
    .sort((a, b) => {
      const aLowStock = a.stock <= a.min_stock;
      const bLowStock = b.stock <= b.min_stock;
      if (aLowStock && !bLowStock) return -1;
      if (!aLowStock && bLowStock) return 1;
      // Si même statut, trier par nom
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

  return (
    <Layout>
      <div className="space-y-6" data-testid="products-page">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-slate-900 mb-2" style={{ fontFamily: 'Manrope, sans-serif' }}>
              Produits
            </h1>
            <p className="text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Gestion des médicaments et produits
            </p>
          </div>
          <div className="flex gap-2">
            {/* Bouton Gérer les catégories */}
            <Dialog open={showCategoryDialog} onOpenChange={(open) => { 
              setShowCategoryDialog(open); 
              if (open) {
                loadCategories(true); // Recharger les catégories à l'ouverture
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
                  <div className="space-y-2 max-h-48 overflow-y-auto mb-4">
                    {categories.length === 0 ? (
                      <p className="text-sm text-slate-500 text-center py-4">Aucune catégorie</p>
                    ) : (
                      categories.map((cat) => (
                        <div key={cat.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div 
                              className="w-4 h-4 rounded-full" 
                              style={{ backgroundColor: cat.color || '#3B82F6' }}
                            />
                            <div>
                              <p className="font-medium text-slate-900">{cat.name}</p>
                              {cat.description && (
                                <p className="text-xs text-slate-500">{cat.description}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-1">
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
                  <div>
                    <Label htmlFor="cat-color">Couleur</Label>
                    <div className="flex gap-2 items-center">
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
                loadCategories(); // Recharger les catégories quand le dialogue s'ouvre
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
                      <Label className="text-sm text-slate-600">Rechercher un produit existant (nom ou code-barres)</Label>
                      <div className="relative mt-2">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" strokeWidth={1.5} />
                        <Input
                          placeholder="Tapez pour rechercher..."
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
                                {product.barcode && (
                                  <p className="text-xs text-slate-500">{product.barcode}</p>
                                )}
                              </div>
                              <span className="text-teal-700 font-medium">{product.price?.toFixed(2)} €</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {productSearchInForm && filteredProductsInForm.length === 0 && (
                        <p className="mt-2 text-sm text-slate-500">Aucun produit trouvé - vous pouvez en créer un nouveau</p>
                      )}
                    </div>
                  )}
                  
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
                      <Label htmlFor="barcode">Code-barres</Label>
                      <Input
                        id="barcode"
                        value={formData.barcode}
                        onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
                        data-testid="product-barcode-input"
                      />
                    </div>
                  </div>
                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="price">Prix (€) *</Label>
                      <Input
                        id="price"
                        type="number"
                        step="0.01"
                        value={formData.price}
                        onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                        required
                        data-testid="product-price-input"
                      />
                    </div>
                    <div>
                      <Label htmlFor="stock">Stock *</Label>
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
                  <div>
                    <Label htmlFor="category">Catégorie</Label>
                    <Select 
                      value={formData.category_id} 
                      onValueChange={(value) => setFormData({ ...formData, category_id: value === 'none' ? '' : value })}
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
              placeholder="Rechercher par nom ou code-barres..."
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
          {currentProducts.map((product) => (
            <div
              key={product.id}
              data-testid={`product-card-${product.id}`}
              className={`p-4 rounded-xl bg-white border transition-all cursor-pointer ${
                product.is_active === false 
                  ? 'border-red-200 bg-red-50/30 opacity-75' 
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
                  </div>
                  {product.barcode && (
                    <p className="text-sm text-slate-500" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
                      {product.barcode}
                    </p>
                  )}
                </div>
                <div className="p-2 bg-teal-50 rounded-lg">
                  <Package className="w-5 h-5 text-teal-700" strokeWidth={1.5} />
                </div>
              </div>
              
              {/* Category Badge */}
              {product.category_id && (
                <div className="mb-3">
                  <span 
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-white"
                    style={{ backgroundColor: getCategoryColor(product.category_id) }}
                  >
                    <Tag className="w-3 h-3" />
                    {getCategoryName(product.category_id)}
                  </span>
                </div>
              )}
              
              <div className="space-y-2 mb-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Prix:</span>
                  <span className="font-medium text-slate-900">{formatAmount(product.price)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Stock:</span>
                  <span className={`font-medium ${product.stock <= product.min_stock ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {product.stock} unités
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
          ))}
        </div>

        {/* Informations de pagination */}
        {filteredProducts.length > 0 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
              Affichage de {startIndex + 1} à {Math.min(endIndex, filteredProducts.length)} sur {filteredProducts.length} produits
            </p>
            <div className="text-sm text-slate-600" style={{ fontFamily: 'Inter, sans-serif' }}>
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
            <p className="text-slate-500" style={{ fontFamily: 'Inter, sans-serif' }}>
              Aucun produit trouvé
            </p>
          </div>
        )}
      </div>

      {/* Dialogue de confirmation de suppression produit */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Confirmer la suppression
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer le produit &ldquo;{productToDelete?.name}&rdquo; ?
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
        <AlertDialogContent className="bg-white/95 backdrop-blur-sm">
          <AlertDialogHeader>
            <AlertDialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
              Supprimer la catégorie
            </AlertDialogTitle>
            <AlertDialogDescription style={{ fontFamily: 'Inter, sans-serif' }}>
              Êtes-vous sûr de vouloir supprimer la catégorie &ldquo;{categoryToDelete?.name}&rdquo; ?
              Les produits associés ne seront pas supprimés mais n&apos;auront plus de catégorie.
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
    </Layout>
  );
};

export default Products;
