import React, { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious, PaginationEllipsis } from '../components/ui/pagination';
import { Plus, Search, Edit, Trash2, Package } from 'lucide-react';
import api from '../services/api';
import { addItem, getAllItems, updateItem, deleteItem as deleteFromDB, addLocalChange, getDB } from '../services/indexedDB';
import { useOffline } from '../contexts/OfflineContext';
import { toast } from 'sonner';

const Products = () => {
  const [products, setProducts] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [productsPerPage] = useState(9);
  const [formData, setFormData] = useState({
    name: '',
    barcode: '',
    description: '',
    price: '',
    stock: '',
    min_stock: '10',
    category: '',
  });
  const { isOnline } = useOffline();

  useEffect(() => {
    loadProducts();
  }, []);

  const refreshData = async () => {
    try {
      // Clear browser cache for API calls
      if ('caches' in window) {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
      }
      
      // Clear IndexedDB
      try {
        const db = await getDB();
        await db.clear('products');
      } catch (error) {
        console.warn('Could not clear IndexedDB:', error);
      }
      
      // Force reload data with no-cache headers
      await loadProducts(true);
    } catch (error) {
      console.error('Error refreshing data:', error);
    }
  };

  const loadProducts = async (forceRefresh = false) => {
    try {
      if (isOnline) {
        // Forcer un nouveau fetch sans cache si demandé
        const headers = forceRefresh ? { 'Cache-Control': 'no-cache' } : {};
        
        const response = await api.get('/products', { headers });
        setProducts(response.data);
        
        // Clear IndexedDB before updating if forced refresh
        if (forceRefresh) {
          try {
            const db = await getDB();
            await db.clear('products');
          } catch (error) {
            console.warn('Could not clear IndexedDB:', error);
          }
        }
        
        // Save to IndexedDB
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const productData = {
        ...formData,
        price: parseFloat(formData.price),
        stock: parseInt(formData.stock),
        min_stock: parseInt(formData.min_stock),
      };

      if (editingProduct) {
        if (isOnline) {
          await api.put(`/products/${editingProduct.id}`, productData);
        } else {
          productData.id = editingProduct.id;
          await updateItem('products', productData);
          await addLocalChange('product', 'update', productData);
        }
        toast.success('Produit mis à jour');
      } else {
        let newProduct;
        if (isOnline) {
          const response = await api.post('/products', productData);
          newProduct = response.data;
          await addItem('products', newProduct);
        } else {
          newProduct = { ...productData, id: Date.now().toString() };
          await addItem('products', newProduct);
          await addLocalChange('product', 'create', newProduct);
        }
        toast.success('Produit ajouté');
      }

      setShowDialog(false);
      resetForm();
      await loadProducts();
    } catch (error) {
      console.error('Error saving product:', error);
      toast.error('Erreur lors de l\'enregistrement');
    }
  };

  const handleDelete = async (productId) => {
    if (!window.confirm('Voulez-vous vraiment supprimer ce produit?')) return;
    
    try {
      if (isOnline) {
        await api.delete(`/products/${productId}`);
      } else {
        await deleteFromDB('products', productId);
        await addLocalChange('product', 'delete', { id: productId });
      }
      toast.success('Produit supprimé');
      loadProducts();
    } catch (error) {
      console.error('Error deleting product:', error);
      toast.error('Erreur lors de la suppression');
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
      category: product.category || '',
    });
    setShowDialog(true);
  };

  const resetForm = () => {
    setEditingProduct(null);
    setFormData({
      name: '',
      barcode: '',
      description: '',
      price: '',
      stock: '',
      min_stock: '10',
      category: '',
    });
  };

  const filteredProducts = products.filter((p) =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.barcode?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculs de pagination
  const totalPages = Math.ceil(filteredProducts.length / productsPerPage);
  const startIndex = (currentPage - 1) * productsPerPage;
  const endIndex = startIndex + productsPerPage;
  const currentProducts = filteredProducts.slice(startIndex, endIndex);

  // Fonction pour changer de page
  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    // Scroll vers le haut quand on change de page
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // Reset à la page 1 quand on recherche
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

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
          <Dialog open={showDialog} onOpenChange={(open) => { setShowDialog(open); if (!open) resetForm(); }}>
            <DialogTrigger asChild>
              <Button data-testid="add-product-button" className="bg-teal-700 hover:bg-teal-800 rounded-full">
                <Plus className="w-4 h-4 mr-2" strokeWidth={1.5} />
                Ajouter un produit
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle style={{ fontFamily: 'Manrope, sans-serif' }}>
                  {editingProduct ? 'Éditer le produit' : 'Nouveau produit'}
                </DialogTitle>
              </DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4" data-testid="product-form">
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
                  <Input
                    id="category"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  />
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

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" strokeWidth={1.5} />
          <Input
            placeholder="Rechercher par nom ou code-barres..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            data-testid="product-search-input"
            className="pl-10"
          />
        </div>

        {/* Products Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {currentProducts.map((product) => (
            <div
              key={product.id}
              data-testid={`product-card-${product.id}`}
              className="p-4 rounded-xl bg-white border border-slate-100 hover:border-teal-200 transition-all cursor-pointer"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <h3 className="font-semibold text-slate-900 mb-1" style={{ fontFamily: 'Manrope, sans-serif' }}>
                    {product.name}
                  </h3>
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
              <div className="space-y-2 mb-3">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-600">Prix:</span>
                  <span className="font-medium text-slate-900">{product.price.toFixed(2)} €</span>
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
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(product.id)}
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
    </Layout>
  );
};

export default Products;